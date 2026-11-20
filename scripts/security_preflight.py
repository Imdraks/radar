"""VPS checks print booleans only; never rotate keys or change SSH access blindly."""

import json
import os
import subprocess
from pathlib import Path


def main():
    root = Path("/opt/radar")
    result = {}
    for name in [".env", ".env.mcp"]:
        file = root / name
        if file.exists():
            result[name + "_private"] = not bool(file.stat().st_mode & 0o077)
    check = """import json
from app.core.config import settings as s
from urllib.parse import urlsplit
print(json.dumps({'production':s.app_env=='production','debug_disabled':not s.debug,'strong_app_secret':len(s.secret_key)>=32 and s.secret_key!='change-this-in-production','strong_jwt_secret':len(s.jwt_secret_key)>=32 and s.jwt_secret_key!='your-jwt-secret-key','https_frontend':urlsplit(s.frontend_url).scheme=='https'}))
"""
    output = subprocess.check_output(
        ["docker", "exec", "radar-backend-1", "python", "-c", check], text=True
    )
    result.update(json.loads(output.strip().splitlines()[-1]))
    result["backup_certificate_present"] = Path(
        os.environ.get("RADAR_BACKUP_CERTIFICATE", "/etc/radar/backup-recipient.pem")
    ).is_file()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(result.values()):
        raise SystemExit(
            "Corriger les points false avant le déploiement. Ne pas remplacer SECRET_KEY sans migration des données existantes."
        )


if __name__ == "__main__":
    main()
