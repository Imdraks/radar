"""Repair the missing Google callback Request parameter, without a DB migration."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

OLD = 'async def google_sso_callback(\n    code: str,'
NEW = 'async def google_sso_callback(\n    request: Request,\n    code: str,'


def patched(source):
    if source.count(NEW) == 1 and OLD not in source:
        return source
    if source.count(OLD) != 1 or 'sso_service.create_session_tokens(user, request=request)' not in source:
        raise RuntimeError('Version SSO non reconnue. Aucun remplacement complet du fichier.')
    result = source.replace(OLD, NEW, 1)
    compile(result, 'sso.py', 'exec')
    return result


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def write(file, data, metadata):
    fd, temporary = tempfile.mkstemp(prefix='.radar-sso-', dir=file.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, metadata.st_mode & 0o777)
        os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.replace(temporary, file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Lancer avec sudo.')
    root = Path('/opt/radar')
    file = root / 'backend/app/api/sso.py'
    if file.resolve() != file:
        parser.error('Lien symbolique refusé.')
    original = file.read_bytes()
    result = patched(original.decode()).encode()
    compose = ['docker', 'compose', '--project-directory', root, '-p', 'radar', '-f', root / 'compose.server.yml', '-f', root / 'compose.mcp.yml']
    services = json.loads(run([*compose, 'config', '--format', 'json'], capture_output=True, text=True).stdout)['services']
    if Path(services['backend']['build']['context']).resolve() != root / 'backend':
        parser.error('Contexte backend inattendu.')
    image_tag = services['backend']['image']
    if any(services[name]['image'] != image_tag for name in ['worker', 'scheduler']):
        parser.error('Images worker/scheduler différentes du backend.')
    if not args.apply:
        print('Correctif reconnu et syntaxe valide. --apply pour sauvegarder et reconstruire.')
        return
    info = json.loads(run(['docker', 'inspect', 'radar-backend-1'], capture_output=True, text=True).stdout)[0]
    if info['Config']['Image'] != image_tag:
        parser.error('Image du backend différente de Compose.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = Path('/opt/radar-deployment-backups') / ('google-sso-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup.parent, 0o700)
    metadata = file.stat()
    (backup / 'sso.py').write_bytes(original)
    (backup / 'image.json').write_text(json.dumps({'tag': image_tag, 'id': info['Image']}))
    run(['docker', 'image', 'tag', info['Image'], 'radar-backend:before-google-sso-' + stamp.lower()])
    restarting = False
    try:
        write(file, result, metadata)
        run([*compose, 'build', 'backend'])
        restarting = True
        run([*compose, 'up', '-d', '--no-deps', '--no-build', 'backend', 'worker', 'scheduler'])
        check = "import inspect; from app.api.sso import google_sso_callback; assert 'request' in inspect.signature(google_sso_callback).parameters"
        run([*compose, 'exec', '-T', 'backend', 'python', '-c', check])
        run([*compose, 'ps', 'backend', 'worker', 'scheduler'])
        print(f'Correctif Google installé. Sauvegarde : {backup}. Aucune migration de base effectuée.')
    except BaseException:
        write(file, original, metadata)
        run(['docker', 'image', 'tag', info['Image'], image_tag])
        if restarting:
            run([*compose, 'up', '-d', '--no-deps', '--no-build', 'backend', 'worker', 'scheduler'])
        raise


if __name__ == '__main__':
    main()
