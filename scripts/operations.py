"""Radar VPS maintenance: private backups, isolated restore drills and honest monitoring."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid


def compose(args, **kwargs):
    root = os.environ.get("RADAR_DEPLOY_DIR", "/opt/radar")
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            root,
            "-f",
            root + "/compose.server.yml",
            "-f",
            root + "/compose.mcp.yml",
            *args,
        ],
        check=True,
        **kwargs,
    )


def postgres(command, **kwargs):
    return compose(["exec", "-T", "postgres", "sh", "-ec", command], **kwargs)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(folder):
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    stamp = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    path = folder / ("radar-" + stamp + ".dump")
    partial = path.with_suffix(".partial")
    try:
        with partial.open("wb") as f:
            postgres(
                'exec pg_dump --lock-wait-timeout=30s --format=custom -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
                stdin=subprocess.DEVNULL,
                stdout=f,
                timeout=600,
            )
        if not partial.stat().st_size:
            raise RuntimeError("Archive vide")
        with partial.open("rb") as f:
            postgres(
                "exec pg_restore --list", stdin=f, stdout=subprocess.DEVNULL, timeout=60
            )
        partial.replace(path)
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sha256": digest(path),
            "bytes": path.stat().st_size,
            "scope": "PostgreSQL uniquement",
            "restore_verified": False,
        }
        meta = path.with_suffix(".json")
        meta.write_text(json.dumps(manifest, indent=2))
        for file in [path, meta]:
            os.chmod(file, 0o600)
        remote = os.environ.get("RADAR_BACKUP_REMOTE", "")
        if remote:
            if remote.startswith("-") or ":" not in remote:
                raise ValueError("RADAR_BACKUP_REMOTE doit être un hôte SSH:répertoire")
            subprocess.run(
                ["rsync", "-a", "--", str(path), str(meta), remote],
                check=True,
                timeout=600,
            )
        print(json.dumps({"backup": str(path), "offsite_copied": bool(remote)}))
        return path
    finally:
        partial.unlink(missing_ok=True)


def drill(path):
    meta = path.with_suffix(".json")
    data = json.loads(meta.read_text())
    if digest(path) != data["sha256"]:
        raise RuntimeError("Empreinte de sauvegarde invalide")
    probe = "radar_restore_probe_" + uuid.uuid4().hex
    # The target is generated internally: no command can select the live database.
    created = False
    try:
        postgres(
            f'createdb -U "$POSTGRES_USER" {probe}',
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
        created = True
        with path.open("rb") as f:
            postgres(
                f'pg_restore --exit-on-error --no-owner --no-acl --single-transaction -U "$POSTGRES_USER" -d {probe}',
                stdin=f,
                stdout=subprocess.DEVNULL,
                timeout=600,
            )
        result = postgres(
            f'psql -U "$POSTGRES_USER" -d {probe} -Atc "SELECT version_num FROM alembic_version; SELECT count(*) FROM users; SELECT count(*) FROM workspaces;"',
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            timeout=30,
        )
        if len(result.stdout.splitlines()) < 3:
            raise RuntimeError("Schéma restauré incomplet")
    finally:
        if created:
            postgres(
                f'dropdb -U "$POSTGRES_USER" {probe}',
                stdin=subprocess.DEVNULL,
                timeout=30,
            )
    data.update(
        restore_verified=True,
        restore_verified_at=datetime.now(timezone.utc).isoformat(),
    )
    meta.write_text(json.dumps(data, indent=2))
    os.chmod(meta, 0o600)
    print(json.dumps({"restore_verified": True, "backup": str(path)}))


def monitor(folder):
    alerts = []
    for service in [
        "backend",
        "frontend",
        "worker",
        "scheduler",
        "postgres",
        "redis",
        "mcp",
    ]:
        result = compose(
            ["ps", "--status", "running", "-q", service],
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
        if not result.stdout.strip():
            alerts.append(service + ": arrêté")
        else:
            inspected = json.loads(
                subprocess.check_output(
                    ["docker", "inspect", result.stdout.decode().strip()]
                )
            )[0]
            if (
                inspected.get("State", {}).get("Health", {}).get("Status")
                == "unhealthy"
            ):
                alerts.append(service + ": contrôle de santé en échec")
    # Real DB/Redis checks inside the deployed backend, without printing config or credentials.
    compose(
        [
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            'from sqlalchemy import create_engine,text; from app.core.config import settings; import redis;\nwith create_engine(settings.database_url).connect() as c: c.execute(text("SELECT 1"))\nassert redis.from_url(settings.redis_url,socket_connect_timeout=2,socket_timeout=2).ping()',
        ],
        stdin=subprocess.DEVNULL,
        timeout=30,
    )
    worker = compose(
        [
            "exec",
            "-T",
            "worker",
            "celery",
            "-A",
            "app.workers.celery_app",
            "inspect",
            "ping",
            "--timeout=5",
        ],
        stdout=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        timeout=20,
    )
    if b"pong" not in worker.stdout:
        alerts.append("Aucun worker Celery ne répond")
    dumps = sorted(folder.glob("radar-*.json"), key=lambda p: p.stat().st_mtime)
    now = datetime.now(timezone.utc)
    if (
        not dumps
        or (
            now
            - datetime.fromisoformat(json.loads(dumps[-1].read_text())["created_at"])
        ).total_seconds()
        > 36 * 3600
    ):
        alerts.append("Sauvegarde PostgreSQL absente ou âgée de plus de 36 h")
    verified = [
        json.loads(p.read_text())
        for p in dumps
        if json.loads(p.read_text()).get("restore_verified")
    ]
    if (
        not verified
        or (
            now - datetime.fromisoformat(verified[-1]["restore_verified_at"])
        ).total_seconds()
        > 8 * 86400
    ):
        alerts.append("Restauration isolée non vérifiée depuis 8 jours")
    usage = shutil.disk_usage(folder if folder.exists() else Path("/opt"))
    if usage.free / usage.total < 0.15:
        alerts.append("Disque : moins de 15 % disponibles")
    print(
        json.dumps(
            {"checked_at": now.isoformat(), "alerts": alerts}, ensure_ascii=False
        )
    )
    if alerts:
        raise SystemExit(1)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "drill", "monitor"])
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("/opt/radar-deployment-backups/scheduled"),
    )
    args = parser.parse_args()
    if args.action == "backup":
        backup(args.directory)
    elif args.action == "monitor":
        monitor(args.directory)
    else:
        drill(backup(args.directory))


if __name__ == "__main__":
    main()
