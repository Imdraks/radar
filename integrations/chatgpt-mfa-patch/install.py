"""Add challenge-based MFA to the known VPS connector. Default is validation only."""
import argparse
import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def transform(source):
    if "from './mfa-login.mjs'" in source:
        raise ValueError('Correctif déjà installé.')
    pattern = re.compile(r'  async login\(email, password, totp_code\) \{\n.*?\n  \}', re.S)
    matches = list(pattern.finditer(source))
    expected = 'f21486f1622bc160c9d941275fdeb4711ce3b6415da6611f4546f65a6c057691'
    if len(matches) != 1 or hashlib.sha256(matches[0].group().encode()).hexdigest() != expected:
        raise ValueError('Version du connecteur non reconnue ; aucun écrasement.')
    return "import { mfaLogin } from './mfa-login.mjs';\n" + pattern.sub(
        '  async login(email, password, totp_code) {\n    return mfaLogin(this, email, password, totp_code);\n  }', source, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('connector', type=Path)
    parser.add_argument('--node-image', default='radar-chatgpt:local')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    target = args.connector / 'src/radar.mjs'
    helper = args.connector / 'src/mfa-login.mjs'
    source = target.read_text()
    payload = Path(__file__).with_name('mfa-login.mjs').read_bytes()
    if "from './mfa-login.mjs'" in source and helper.is_file() and helper.read_bytes() == payload:
        print('Correctif MFA déjà présent.')
        return
    if target.is_symlink() or helper.exists() or helper.is_symlink():
        parser.error('Lien ou module préexistant non reconnu ; aucun écrasement.')
    try:
        patched = transform(source).encode()
    except ValueError as error:
        parser.error(str(error))
    for code in [patched, payload]:
        subprocess.run(['docker', 'run', '--rm', '--pull=never', '--network=none', '-i',
            '--entrypoint', 'node', args.node_image, '--input-type=module', '--check'], input=code, check=True)
    print('Connecteur reconnu et syntaxe valide. Arrêter uniquement le MCP avant --apply.')
    if not args.apply:
        return
    backup = args.connector / '.mfa-patch-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(target, backup / target.name)
    owner = target.stat()
    try:
        for file, content in [(helper, payload), (target, patched)]:
            fd, name = tempfile.mkstemp(prefix='.mfa-patch-', dir=file.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(content)
                os.chmod(name, owner.st_mode & 0o777)
                if os.geteuid() == 0:
                    os.chown(name, owner.st_uid, owner.st_gid)
                os.replace(name, file)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
    except Exception:
        shutil.copy2(backup / target.name, target)
        helper.unlink(missing_ok=True)
        raise
    print(f'Correctif installé, sauvegarde : {backup}. Reconstruire puis redémarrer uniquement mcp.')


if __name__ == '__main__':
    main()
