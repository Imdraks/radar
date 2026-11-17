"""Deploy password recovery and MFA-protected password change on the owner's existing VPS.
No schema migration, payment, password reset, env/Compose/Nginx change.
"""
import argparse
from datetime import datetime, timezone
import difflib
import io
import tarfile
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request

BASE = '5a3e019ea6388e30360fcb30aa792a09d2251724'
TARGET = 'a487e9de50e1644dd28cda84b6331f8b68376a1f'
FILES = ['backend/app/api/mfa.py', 'backend/app/api/passwords.py', 'backend/app/api/users.py', 'backend/app/api/workspace.py', 'backend/app/core/mfa.py', 'backend/app/core/passwords.py', 'backend/app/core/security_middleware.py', 'backend/app/main.py', 'backend/app/schemas/user.py', 'backend/app/services/mfa_delivery.py', 'backend/app/services/password_email.py', 'backend/app/services/password_recovery.py', 'backend/app/workers/celery_app.py', 'backend/app/workers/password_tasks.py', 'frontend/next.config.js', 'frontend/src/app/forgot-password/page.tsx', 'frontend/src/app/login/page.tsx', 'frontend/src/app/reset-password/page.tsx', 'frontend/src/app/settings/page.tsx', 'frontend/src/app/workspaces/[id]/page.tsx', 'frontend/src/components/CookieConsent.tsx', 'frontend/src/components/auth/PasswordFields.tsx', 'frontend/src/components/auth/PasswordRecovery.tsx', 'frontend/src/components/settings/PasswordSettings.tsx', 'frontend/src/components/settings/TwoFactorSettings.tsx', 'frontend/src/components/settings/WorkspaceSettings.tsx', 'frontend/src/content/documentation.ts', 'frontend/src/lib/api.ts']
NEW_FILES = {'backend/app/api/passwords.py', 'backend/app/services/password_email.py', 'frontend/src/app/reset-password/page.tsx', 'backend/app/services/password_recovery.py', 'frontend/src/components/auth/PasswordFields.tsx', 'frontend/src/components/settings/PasswordSettings.tsx', 'frontend/src/app/forgot-password/page.tsx', 'frontend/src/components/auth/PasswordRecovery.tsx', 'backend/app/core/passwords.py', 'backend/app/workers/password_tasks.py'}
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


def fetch_files(revision):
    url = f'https://codeload.github.com/Imdraks/radar/tar.gz/{revision}'
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read(64 * 1024 * 1024 + 1)
    if len(payload) > 64 * 1024 * 1024:
        raise RuntimeError('Archive trop volumineuse.')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        for member in archive:
            name = member.name.partition('/')[2]
            if name in FILES:
                if not member.isfile() or member.size > 1024 * 1024:
                    raise RuntimeError('Fichier non régulier ou trop volumineux.')
                files[name] = archive.extractfile(member).read()
    return files


def make_patch(root, before, after):
    result = []
    for name in FILES:
        file = root / name
        if file.resolve() != file or (file.exists() and not file.is_file()):
            raise RuntimeError(f'Lien ou fichier non régulier refusé : {name}')
        if name not in after or (name not in before and name not in NEW_FILES):
            raise RuntimeError(f'Livraison incomplète : {name}')
        current = file.read_bytes() if file.exists() else None
        if current == after[name]:
            continue
        if name in NEW_FILES and current is not None:
            raise RuntimeError(f'Un fichier nouveau existe avec un contenu non reconnu : {name}')
        old = before.get(name)
        result.extend(difflib.unified_diff((old or b'').decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True), fromfile='a/' + name if old is not None else '/dev/null', tofile='b/' + name))
    return ''.join(result).encode()


def write(file, data, metadata):
    file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.radar-password-', dir=file.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, metadata.st_mode & 0o777 if metadata else 0o644)
        owner = metadata or file.parent.stat()
        os.chown(temporary, owner.st_uid, owner.st_gid)
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
    revision_code = "from sqlalchemy import create_engine,text; from app.core.config import settings; c=create_engine(settings.database_url).connect(); print(','.join(c.execute(text('select version_num from alembic_version')).scalars()))"
    revision = run(['docker', 'exec', 'radar-backend-1', 'python', '-c', revision_code], capture_output=True, text=True).stdout.strip()
    if revision != '058_revocable_sessions':
        parser.error(f'Révision 058 requise ; reçue {revision!r}. Aucun changement.')
    before = fetch_files(BASE)
    after = fetch_files(TARGET)
    # Earlier VPS public-doc deployment predates the MFA guide. Accept only
    # that complete reviewed baseline, without overwriting other local edits.
    guide = 'frontend/src/content/documentation.ts'
    if guide in FILES and (root / guide).is_file() and (root / guide).read_bytes() != after.get(guide):
        older = download('fea31f45df4154677febd43bc01412327150490e', guide)
        if (root / guide).read_bytes() == older:
            before[guide] = older
    patch = make_patch(root, before, after)
    if patch:
        run(['git', 'apply', '--check', '-'], cwd=root, input=patch)
    original = {name: ((root / name).read_bytes(), (root / name).stat()) if (root / name).exists() else (None, None) for name in FILES}
    with tempfile.TemporaryDirectory(prefix='radar-password-update-') as temporary:
        stage = Path(temporary)
        os.chmod(stage, 0o700)
        for directory in ['backend', 'frontend']:
            shutil.copytree(root / directory, stage / directory, symlinks=True,
                ignore=shutil.ignore_patterns('node_modules', '.next', '.venv', '.git', '__pycache__', '*.log'))
        if patch:
            run(['git', 'apply', '-'], cwd=stage, input=patch)
        for name in FILES:
            if name.startswith('backend/') and name.endswith('.py'):
                compile((stage / name).read_bytes(), name, 'exec')
        if not args.apply:
            print('Compatibilité vérifiée. Aucun fichier du site modifié. --apply pour déployer.')
            return
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = args.backup_root.resolve() / ('password-recovery-' + stamp)
        backup.mkdir(parents=True, mode=0o700)
        os.chmod(backup.parent, 0o700)
        manifest = {}
        for index, (name, (content, metadata)) in enumerate(original.items()):
            saved = backup / f'source-{index}'
            if content is not None:
                saved.write_bytes(content)
            manifest[name] = {'backup': saved.name, 'mode': metadata.st_mode & 0o777, 'uid': metadata.st_uid, 'gid': metadata.st_gid} if metadata else None
        (backup / 'sources.json').write_text(json.dumps(manifest, indent=2))
        images, overlay = {}, {'services': {}}
        for service in ['backend', 'frontend']:
            info = json.loads(run(['docker', 'inspect', f'radar-{service}-1'], capture_output=True, text=True).stdout)[0]
            tag = info['Config']['Image']
            if config[service].get('image', tag) != tag:
                raise RuntimeError('Tag image en cours différent de Compose.')
            run(['docker', 'image', 'tag', info['Image'], f'radar-{service}:before-password-recovery-{stamp.lower()}'])
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
                if file.resolve() != file or (file.read_bytes() if file.exists() else None) != content:
                    raise RuntimeError(f'Source modifiée pendant la construction : {name}. Aucun écrasement.')
            stopped = True
            run([*compose, 'stop', *SERVICES])
            for name in FILES:
                file = root / name
                if file.resolve() != file or (file.read_bytes() if file.exists() else None) != original[name][0]:
                    raise RuntimeError(f'Source modifiée avant écriture : {name}')
                written.append(name)
                write(root / name, (stage / name).read_bytes(), original[name][1])
            run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
            check = "from app.main import app; from app.core.passwords import POLICY; p={r.path for r in app.routes}; assert POLICY['reset_expiry_minutes']==15; assert '/api/v1/auth/forgot-password' in p; assert '/api/v1/auth/password/change' in p"
            healthy = False
            for attempt in range(30):
                try:
                    run([*compose, 'exec', '-T', 'backend', 'python', '-c', check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    for path in ['/login', '/forgot-password', '/reset-password']:
                        with urllib.request.urlopen('http://127.0.0.1:13000' + path, timeout=3) as response:
                            assert response.status == 200
                    healthy = True
                except Exception:
                    healthy = False
                if healthy:
                    break
                time.sleep(2)
            if not healthy:
                raise RuntimeError('Vérification du correctif et du frontend non confirmée.')
            worker_check = "from app.workers.celery_app import celery_app; i=celery_app.control.inspect(timeout=3); r=i.registered() or {}; q=i.active_queues() or {}; assert any(any(t.split(' [',1)[0]=='app.workers.password_tasks.request_password_reset' for t in tasks) and any(x.get('name')=='celery' for x in q.get(name,[])) for name,tasks in r.items()), 'Worker de récupération absent ou file celery non consommée'"
            worker_ready = False
            for attempt in range(8):
                try:
                    run([*compose, 'exec', '-T', 'backend', 'python', '-c', worker_check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                    worker_ready = True
                    break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    time.sleep(2)
            if not worker_ready:
                raise RuntimeError('Worker de récupération absent ou file celery non consommée.')
            email_check = "from app.services.mfa_delivery import availability; print('Envoi e-mail configuré :', 'oui (réception réelle à tester)' if availability()['email'] else 'non — configurer Resend ou SMTP TLS/SSL')"
            run([*compose, 'exec', '-T', 'backend', 'python', '-c', email_check])
            run([*compose, 'ps', *SERVICES])
            print('Correctif installé. Aucune migration et aucun mot de passe modifié.', flush=True)
        except BaseException:
            for name in reversed(written):
                if original[name][0] is None:
                    (root / name).unlink(missing_ok=True)
                else:
                    write(root / name, original[name][0], original[name][1])
            for tag, image in images.items():
                run(['docker', 'image', 'tag', image, tag])
            if stopped:
                run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
            print(f'Échec : anciennes sources et images rétablies. Sauvegardes : {backup}', flush=True)
            raise


if __name__ == '__main__':
    main()
