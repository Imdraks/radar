"""Deploy the reviewed password-prompt fix on the owner's existing VPS.
No schema migration, payment, password reset, env/Compose/Nginx change.
"""
import argparse
from datetime import datetime, timezone
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request

BASE = '5a3e019ea6388e30360fcb30aa792a09d2251724'
TARGET = '477e3a88b4c574a37d92bff320f0482276996248'
FILES = ['backend/app/api/mfa.py', 'backend/app/core/mfa.py',
         'frontend/src/components/settings/TwoFactorSettings.tsx']
SERVICES = ['backend', 'worker', 'scheduler', 'frontend']


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def download(revision, name):
    url = f'https://raw.githubusercontent.com/Imdraks/radar/{revision}/{name}'
    with urllib.request.urlopen(url, timeout=30) as response:
        result = response.read(1024 * 1024 + 1)
    if len(result) > 1024 * 1024:
        raise RuntimeError('Fichier de livraison trop volumineux.')
    return result


def make_patch(root, before, after):
    result = []
    for name in FILES:
        file = root / name
        if file.resolve() != file or not file.is_file():
            raise RuntimeError(f'Fichier absent ou lien refusé : {name}')
        if file.read_bytes() == after[name]:
            continue
        result.extend(difflib.unified_diff(before[name].decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True), fromfile='a/' + name, tofile='b/' + name))
    return ''.join(result).encode()


def write(file, data, metadata):
    fd, temporary = tempfile.mkstemp(prefix='.radar-password-', dir=file.parent)
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
    parser.add_argument('--root', type=Path, default=Path('/opt/radar'))
    parser.add_argument('--backup-root', type=Path, default=Path('/opt/radar-deployment-backups'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Lancer avec sudo.')
    root = args.root.resolve()
    compose = ['docker', 'compose', '--project-directory', root, '-p', 'radar',
               '-f', root / 'compose.server.yml', '-f', root / 'compose.mcp.yml']
    config = json.loads(run([*compose, 'config', '--format', 'json'], capture_output=True, text=True).stdout)['services']
    for service in ['backend', 'frontend']:
        if Path(config[service]['build']['context']).resolve() != root / service:
            parser.error(f'Contexte {service} non reconnu.')
    if any(config[name].get('image') != config['backend'].get('image') for name in ['worker', 'scheduler']):
        parser.error('Images worker/scheduler différentes du backend.')
    before = {name: download(BASE, name) for name in FILES}
    after = {name: download(TARGET, name) for name in FILES}
    patch = make_patch(root, before, after)
    if patch:
        run(['git', 'apply', '--check', '-'], cwd=root, input=patch)
    original = {name: ((root / name).read_bytes(), (root / name).stat()) for name in FILES}
    with tempfile.TemporaryDirectory(prefix='radar-password-update-') as temporary:
        stage = Path(temporary)
        os.chmod(stage, 0o700)
        for directory in ['backend', 'frontend']:
            shutil.copytree(root / directory, stage / directory, symlinks=True,
                ignore=shutil.ignore_patterns('node_modules', '.next', '.venv', '.git', '__pycache__', '*.log'))
        if patch:
            run(['git', 'apply', '-'], cwd=stage, input=patch)
        for name in FILES[:2]:
            compile((stage / name).read_bytes(), name, 'exec')
        if not args.apply:
            print('Compatibilité vérifiée. Aucun fichier du site modifié. --apply pour déployer.')
            return
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = args.backup_root.resolve() / ('password-prompt-' + stamp)
        backup.mkdir(parents=True, mode=0o700)
        os.chmod(backup.parent, 0o700)
        manifest = {}
        for index, (name, (content, metadata)) in enumerate(original.items()):
            saved = backup / f'source-{index}'
            saved.write_bytes(content)
            manifest[name] = {'backup': saved.name, 'mode': metadata.st_mode & 0o777, 'uid': metadata.st_uid, 'gid': metadata.st_gid}
        (backup / 'sources.json').write_text(json.dumps(manifest, indent=2))
        images, overlay = {}, {'services': {}}
        for service in ['backend', 'frontend']:
            info = json.loads(run(['docker', 'inspect', f'radar-{service}-1'], capture_output=True, text=True).stdout)[0]
            tag = info['Config']['Image']
            if config[service].get('image', tag) != tag:
                raise RuntimeError('Tag image en cours différent de Compose.')
            run(['docker', 'image', 'tag', info['Image'], f'radar-{service}:before-password-prompt-{stamp.lower()}'])
            images[tag] = info['Image']
            overlay['services'][service] = {'image': tag, 'build': {'context': str(stage / service)}}
        (backup / 'images.json').write_text(json.dumps(images, indent=2))
        override = stage / 'build.json'
        override.write_text(json.dumps(overlay))
        stopped, written = False, []
        try:
            print(f'Sauvegardes : {backup}. Construction avant interruption du site.', flush=True)
            run([*compose, '-f', override, 'build', 'backend', 'frontend'])
            for name, (content, _) in original.items():
                file = root / name
                if file.resolve() != file or file.read_bytes() != content:
                    raise RuntimeError(f'Source modifiée pendant la construction : {name}. Aucun écrasement.')
            stopped = True
            run([*compose, 'stop', *SERVICES])
            for name in FILES:
                written.append(name)
                write(root / name, (stage / name).read_bytes(), original[name][1])
            run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
            check = "import inspect; from app.core.mfa import reject; from app.api.mfa import reauth_start; assert 'detail' in inspect.signature(reject).parameters; assert 'Mot de passe Radar incorrect.' in inspect.getsource(reauth_start)"
            healthy = False
            for attempt in range(30):
                try:
                    run([*compose, 'exec', '-T', 'backend', 'python', '-c', check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with urllib.request.urlopen('http://127.0.0.1:13000/login', timeout=3) as response:
                        healthy = response.status == 200
                except Exception:
                    healthy = False
                if healthy:
                    break
                time.sleep(2)
            if not healthy:
                raise RuntimeError('Vérification du correctif et du frontend non confirmée.')
            run([*compose, 'ps', *SERVICES])
            print('Correctif installé. Aucune migration et aucun mot de passe modifié.', flush=True)
        except BaseException:
            for name in reversed(written):
                write(root / name, original[name][0], original[name][1])
            for tag, image in images.items():
                run(['docker', 'image', 'tag', image, tag])
            if stopped:
                run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
            print(f'Échec : anciennes sources et images rétablies. Sauvegardes : {backup}', flush=True)
            raise


if __name__ == '__main__':
    main()
