"""Run a real dump/restore drill against an explicitly disposable Docker PostgreSQL."""

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
        raise RuntimeError("Le conteneur doit annoncer une base de test")
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
        with tempfile.TemporaryDirectory(prefix="radar-restore-test-") as folder:
            path = operations.backup(Path(folder))
            operations.drill(path)
            assert (
                json.loads(path.with_suffix(".json").read_text())["restore_verified"]
                is True
            )
            path.write_bytes(path.read_bytes() + b"corruption")
            try:
                operations.drill(path)
            except RuntimeError as error:
                assert "Empreinte" in str(error)
            else:
                raise AssertionError("Corrupted dump accepted")
            path.write_bytes(b'not a PostgreSQL archive')
            manifest=json.loads(path.with_suffix('.json').read_text())
            manifest['sha256']=operations.digest(path)
            path.with_suffix('.json').write_text(json.dumps(manifest))
            try:
                operations.drill(path)
            except subprocess.CalledProcessError:
                pass
            else:
                raise AssertionError('Invalid restore accepted')
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
            "PASS real dump, isolated restoration, checksum refusal, source rows preserved and probe DB removed"
        )
    finally:
        command(["dropdb", "-U", user, db], stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
