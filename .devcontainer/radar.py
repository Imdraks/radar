"""Private, disposable Codespaces launcher; never targets the application's DB config."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".devcontainer" / ".local"
DATABASE_URL = "postgresql://radar_test:codespaces-test-only@postgres:5432/radar_codespaces_test"
MARKER = "_radar_codespaces_sandbox"


def require_sandbox():
    if os.environ.get("RADAR_CODESPACES_SANDBOX") != "1":
        raise RuntimeError("Commande réservée au conteneur Radar de test.")


def configuration():
    require_sandbox()
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = STATE / "account.json"
    if not path.exists():
        data = {
            "instance_id": secrets.token_hex(24),
            "email": "test@radar.example",
            "password": "Radar!" + secrets.token_urlsafe(24),
            "secret_key": secrets.token_urlsafe(48),
            "jwt_secret_key": secrets.token_urlsafe(48),
        }
        # Exclusive creation, restrictive permissions, no credentials in logs or Git.
        with open(path, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            json.dump(data, stream)
    return json.loads(path.read_text())


def environment(data):
    env = os.environ.copy()
    name = env.get("CODESPACE_NAME", "")
    domain = env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    frontend = f"https://{name}-3000.{domain}" if name else "http://localhost:3000"
    # Always override inherited DB/queue/auth settings. Never load the repository .env.
    env.update({
        "DATABASE_URL": DATABASE_URL,
        "REDIS_URL": "redis://redis:6379/0",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "CELERY_RESULT_BACKEND": "redis://redis:6379/1",
        "SECRET_KEY": data["secret_key"],
        "JWT_SECRET_KEY": data["jwt_secret_key"],
        "ADMIN_PASSWORD": data["password"],
        "APP_ENV": "development", "DEBUG": "false",
        "FRONTEND_URL": frontend, "BACKEND_URL": "http://127.0.0.1:8000",
        "INTERNAL_API_URL": "http://127.0.0.1:8000", "NEXT_PUBLIC_API_URL": "",
        "SEND_INVITATION_EMAILS": "false", "REQUIRE_WORKSPACE_INVITE": "true",
        "PYTHONPATH": str(ROOT / "backend"),
        "VIBERATE_ENABLED": "false",
    })
    # No inherited mail, payment, AI or OAuth credentials in this disposable preview.
    for key in (
        "SMTP_USER", "SMTP_PASSWORD", "IMAP_USER", "IMAP_PASSWORD", "RESEND_API_KEY",
        "REVOLUT_CLIENT_ID", "REVOLUT_PRIVATE_KEY_PATH", "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", "APPLE_CLIENT_ID", "APPLE_PRIVATE_KEY", "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET", "OPENAI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY",
        "TICKETMASTER_API_KEY", "DISCORD_WEBHOOK_URL", "SLACK_WEBHOOK_URL",
    ):
        env.pop(key, None)
    return env


def initialize_database(engine, data):
    """Only initialize an empty schema; subsequent launches require our instance marker."""
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.db import models  # noqa: F401: register all model tables
    from app.db.models.artist_event import ArtistEvent  # noqa: F401
    from app.db.models.user import User, Role
    from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
    from app.core.security import get_password_hash

    with engine.begin() as conn:
        # Serializes bootstrap during overlapping container lifecycle commands.
        conn.execute(text("SELECT pg_advisory_xact_lock(728410320)"))
        tables = inspect(conn).get_table_names()
        if tables:
            if MARKER not in tables:
                raise RuntimeError("Base non vide et non reconnue : aucune modification effectuée.")
            instance = conn.execute(text(f"SELECT instance_id FROM {MARKER}")).scalar_one()
            if instance != data["instance_id"]:
                raise RuntimeError("Cette base appartient à une autre préversion ; démarrage refusé.")
            return False
        # Test schema only. No Alembic stamping or historical migration rewrite.
        Base.metadata.create_all(conn)
        conn.execute(text(f"CREATE TABLE {MARKER} (instance_id TEXT PRIMARY KEY)"))
        conn.execute(text(f"INSERT INTO {MARKER} VALUES (:instance)"), {"instance": data["instance_id"]})
        with Session(bind=conn) as db:
            user = User(email=data["email"], hashed_password=get_password_hash(data["password"]),
                        full_name="TEST — Radar Codespaces", role=Role.ADMIN,
                        is_active=True, is_whitelisted=True, is_superuser=False)
            db.add(user)
            db.flush()
            workspace = Workspace(name="TEST — Codespaces (données jetables)",
                                  owner_user_id=user.id, plan="business", enabled_packs=["core"],
                                  addons=[], max_seats=3)
            db.add(workspace)
            db.flush()
            db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.ADMIN))
            db.commit()
    return True


def bootstrap():
    require_sandbox()
    # Only this literal internal compose target is accepted. No configurable DB URL.
    from sqlalchemy import create_engine
    from app.core.config import settings
    if settings.database_url != DATABASE_URL:
        raise RuntimeError("La configuration ne désigne pas la base Codespaces jetable.")
    engine = create_engine(DATABASE_URL)
    try:
        created = initialize_database(engine, configuration())
    finally:
        engine.dispose()
    print("Base de test initialisée." if created else "Base de test conservée.")


def launch(name, command, cwd, env):
    pidfile = STATE / f"{name}.pid"
    if running_pid(pidfile) is not None:
        return
    with (STATE / f"{name}.log").open("a") as output:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=output, start_new_session=True)
    pidfile.write_text(json.dumps({"pid": process.pid, "identity": process_identity(process.pid)}))


def process_identity(pid):
    """PID numbers can be reused after a Codespace restart; never kill a new process."""
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    if fields[0] == "Z":
        raise ProcessLookupError("Processus terminé")
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return [boot, fields[19]]


def running_pid(path):
    try:
        record = json.loads(path.read_text())
        pid = record["pid"]
        if type(pid) is int and pid > 1 and record["identity"] == process_identity(pid):
            return pid
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        pass
    return None


def wait_http(url, seconds):
    # Loopback readiness must not go through the external HTTP proxy.
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=3) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("Démarrage incomplet. Consulter .devcontainer/.local/*.log puis relancer start.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "start", "stop", "credentials", "_bootstrap", "_worker-ready"])
    args = parser.parse_args()
    data = configuration()
    env = environment(data)
    python = str(STATE / "venv" / "bin" / "python")
    if args.action == "credentials":
        print(f"Email : {data['email']}\nMot de passe : {data['password']}")
        return
    if args.action == "stop":
        for name in ("frontend", "worker", "backend"):
            path = STATE / f"{name}.pid"
            if path.exists():
                pid = running_pid(path)
                if pid is not None:
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                path.unlink()
        print("Services de test arrêtés.")
        return
    if args.action == "_bootstrap":
        bootstrap()
        return
    if args.action == "_worker-ready":
        from app.workers.celery_app import celery_app
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                if celery_app.control.ping(destination=["radar-preview@" + socket.gethostname()], timeout=1):
                    return
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("Worker indisponible : consulter .devcontainer/.local/worker.log.")
    # Ignored state directory contains no .env; prevents accidental dotenv loading.
    subprocess.run([python, str(Path(__file__).resolve()), "_bootstrap"], cwd=STATE, env=env, check=True)
    if args.action == "init":
        return
    launch("backend", [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], STATE, env)
    wait_http("http://127.0.0.1:8000/health", 45)
    launch("worker", [python, "-m", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info",
                      "--hostname=radar-preview@%h", "--concurrency=1", "-Q",
                      "celery,ingestion_standard,web_enrichment,dossier_builder_gpt"], STATE, env)
    subprocess.run([python, str(Path(__file__).resolve()), "_worker-ready"], cwd=STATE, env=env, check=True)
    launch("frontend", ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"], ROOT / "frontend", env)
    wait_http("http://127.0.0.1:3000/login", 180)
    print("Radar prêt : ouvrir le port privé 3000 dans l’onglet Ports.")
    print("Identifiants : python .devcontainer/radar.py credentials")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
