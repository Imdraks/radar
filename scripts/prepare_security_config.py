"""Create only a missing data key; never replace legacy SECRET_KEY or JWT_SECRET_KEY."""

import base64
import os
import secrets
import tempfile
import re
from pathlib import Path


def prepare(root):
    path = root / ".env"
    if path.is_symlink() or (root / ".env.mcp").is_symlink():
        raise RuntimeError(
            "Configuration liée : contrôler les permissions et la préparation manuellement."
        )
    text = path.read_text()
    pattern = re.compile(r"^\s*(?:export\s+)?DATA_ENCRYPTION_KEY\s*=\s*(.*?)\s*$")
    lines = [pattern.match(line) for line in text.splitlines() if pattern.match(line)]
    value = lines[-1].group(1).strip().strip("\"'") if lines else ""
    if value:
        if len(base64.urlsafe_b64decode(value)) != 32:
            raise ValueError(
                "DATA_ENCRYPTION_KEY invalide : traitement manuel requis sans rotation aveugle."
            )
    else:
        key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        text = (
            "\n".join(line for line in text.splitlines() if not pattern.match(line))
            + "\nDATA_ENCRYPTION_KEY="
            + key
            + "\n"
        )
        fd, temporary = tempfile.mkstemp(prefix=".radar-security-", dir=root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(text)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    os.chmod(path, 0o600)
    if (root / ".env.mcp").exists():
        os.chmod(root / ".env.mcp", 0o600)
    print(
        "Configuration privée prête ; clés historiques conservées, aucune valeur affichée."
    )


if __name__ == "__main__":
    os.umask(0o077)
    prepare(Path("/opt/radar"))
