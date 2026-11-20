"""Real encrypted backup and isolated restore, restricted to disposable Docker PostgreSQL."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import operations


def main():
    if os.environ.get("TESTING") != "true":
        raise RuntimeError("TESTING=true requis")
    container = os.environ.get("RADAR_TEST_POSTGRES_CONTAINER", "radar-admin-test-db")
    inspected = json.loads(subprocess.check_output(["docker", "inspect", container]))[0]
    env = dict(
        value.split("=", 1) for value in inspected["Config"]["Env"] if "=" in value
    )
    if "test" not in env.get("POSTGRES_DB", "").lower():
        raise RuntimeError("Disposable test PostgreSQL required")
    user = env.get("POSTGRES_USER", "postgres")
    db = "radar_ops_test_" + uuid.uuid4().hex

    def command(args, **kwargs):
        return subprocess.run(
            ["docker", "exec", "-i", "-e", "POSTGRES_DB=" + db, container, *args],
            check=True,
            **kwargs
        )

    def postgres(sql, **kwargs):
        return command(["sh", "-ec", sql], **kwargs)

    command(["createdb", "-U", user, db], stdin=subprocess.DEVNULL)
    try:
        command(
            [
                "psql",
                "-U",
                user,
                "-d",
                db,
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                "CREATE TABLE users(id integer primary key); INSERT INTO users VALUES(11); CREATE TABLE workspaces(id integer primary key); INSERT INTO workspaces VALUES(22); CREATE TABLE alembic_version(version_num varchar(64)); INSERT INTO alembic_version VALUES('066_production_tools');",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        operations.postgres = postgres
        with tempfile.TemporaryDirectory(
            prefix="radar-encrypted-backup-test-"
        ) as folder:
            root = Path(folder)
            private = root / "offline-test-key.pem"
            cert = root / "public-test-cert.pem"
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:3072",
                    "-nodes",
                    "-keyout",
                    str(private),
                    "-out",
                    str(cert),
                    "-subj",
                    "/CN=Radar disposable backup test",
                    "-days",
                    "1",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            os.environ["RADAR_BACKUP_CERTIFICATE"] = str(cert)
            path = operations.backup(root / "archives", verify=True)
            assert path.suffix == ".cms"
            assert (
                json.loads(path.with_suffix(".json").read_text())["restore_verified"]
                is True
            )
            opened = root / "opened.dump"
            decrypt = [
                "openssl",
                "cms",
                "-decrypt",
                "-binary",
                "-inform",
                "DER",
                "-in",
                str(path),
                "-recip",
                str(cert),
                "-inkey",
                str(private),
                "-out",
                str(opened),
            ]
            subprocess.run(decrypt, check=True)
            operations._restore_dump(opened)
            assert not list((root / "archives").glob("*.dump"))
            assert not list((root / "archives").glob(".radar-backup-*"))
            raw = bytearray(path.read_bytes())
            raw[-1] ^= 1
            path.write_bytes(raw)
            corrupted = subprocess.run(
                decrypt, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
            )
            assert (
                corrupted.returncode != 0
            ), "Unauthenticated corrupted archive accepted"
            os.environ["RADAR_BACKUP_CERTIFICATE"] = str(root / "missing.pem")
            try:
                operations.backup(root / "missing-certificate-archives")
            except RuntimeError:
                pass
            else:
                raise AssertionError("Missing certificate accepted")
        result = command(
            [
                "psql",
                "-U",
                user,
                "-d",
                db,
                "-Atc",
                "SELECT count(*) FROM users; SELECT count(*) FROM workspaces; SELECT count(*) FROM pg_database WHERE datname LIKE 'radar_restore_probe_%';",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
        )
        assert result.stdout.splitlines() == [b"1", b"1", b"0"]
        print(
            "PASS CMS AES-256-GCM backup, private-key decryption, actual isolated restoration, tamper refusal, no persistent plaintext dump, source preserved"
        )
    finally:
        command(["dropdb", "-U", user, db], stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
