"""Deploy the pinned MFA/session patch on the owner's non-Git VPS. Root required.
Default: inspect and stage only. --apply: backup, build, migrate, restart.
Never change Compose/env/Nginx or restore a database automatically.
"""
import argparse
import difflib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from datetime import datetime, timezone

BASE = 'fea31f45df4154677febd43bc01412327150490e'
TARGET = '90f6758bde238ac0d7a4d2f2896012d1a953e05f'
SERVICES = ['backend', 'worker', 'scheduler', 'mcp', 'frontend']


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def archive(revision, paths):
    url = f'https://codeload.github.com/Imdraks/radar/tar.gz/{revision}'
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read(64 * 1024 * 1024 + 1)
    if len(payload) > 64 * 1024 * 1024:
        raise RuntimeError('Archive trop volumineuse.')
    result = {}
    # Read selected regular files; never extract an untrusted archive path.
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as bundle:
        for member in bundle:
            relative = member.name.partition('/')[2]
            if relative in paths:
                if not member.isfile() or member.size > 2 * 1024 * 1024:
                    raise RuntimeError('Fichier de livraison non régulier ou trop volumineux.')
                result[relative] = bundle.extractfile(member).read()
    return result


def known_vps_auth(previous):
    """The complete owner-supplied JSON refresh variant; no heuristic overwrite."""
    old_import = 'from fastapi import APIRouter, Depends, HTTPException, status, Request, Header\n'
    old_refresh = '''@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
'''
    new_refresh = '''class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_token: Optional[str] = None,
    db: Session = Depends(get_db),
    payload: Optional[RefreshTokenRequest] = Body(default=None),
):
    """Refresh access token"""
    # JSON avoids putting credentials in URLs; preserve legacy query clients.
    if payload is not None:
        if refresh_token is not None and refresh_token != payload.refresh_token:
            raise HTTPException(status_code=400, detail="Conflicting refresh credentials")
        refresh_token = payload.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=422, detail="Refresh token is required")
'''
    source = previous.decode()
    if source.count(old_import) != 1 or source.count(old_refresh) != 1:
        raise RuntimeError('Référence auth.py inattendue.')
    return source.replace(old_import, old_import.rstrip('\n') + ', Body\n', 1).replace(old_refresh, new_refresh, 1).encode()


def prepare_patch(root, paths, before, after):
    chunks = []
    for name in paths:
        file = root / name
        if file.is_symlink() or file.resolve() != file:
            raise RuntimeError(f'Lien symbolique refusé : {name}')
        if name not in after:
            raise RuntimeError(f'Livraison incomplète : {name}')
        current = file.read_bytes() if file.exists() else None
        if current == after[name]:
            continue
        # git apply with exact context preserves unrelated local changes and
        # refuses conflicts, missing baseline files or existing unknown additions.
        previous = before.get(name)
        if name == 'backend/app/api/auth.py' and previous is not None and b'def refresh_token(' in previous:
            reviewed_variant = known_vps_auth(previous)
            if current == reviewed_variant:
                previous = reviewed_variant
        chunks.extend(difflib.unified_diff(
            (previous or b'').decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True),
            fromfile='a/' + name if previous is not None else '/dev/null', tofile='b/' + name))
    return ''.join(chunks).encode()


def write_file(file, content, metadata):
    file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.radar-mfa-', dir=file.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, metadata.st_mode & 0o777 if metadata else 0o644)
        owner = metadata or file.parent.stat()
        os.chown(temporary, owner.st_uid, owner.st_gid)
        os.replace(temporary, file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_config(root, config):
    services = config['services']
    for name, directory in [('backend', 'backend'), ('frontend', 'frontend'), ('mcp', 'chatgpt-connector')]:
        build = services[name].get('build', {})
        if not isinstance(build, dict) or Path(build.get('context', '')).resolve() != root / directory:
            raise RuntimeError(f'Contexte Docker inattendu pour {name}.')
    backend_image = services['backend'].get('image')
    for name in ['worker', 'scheduler']:
        if not backend_image or services[name].get('image') != backend_image or services[name].get('build'):
            raise RuntimeError(f'Image partagée backend/{name} non reconnue.')
    for name in SERVICES:
        for mount in services[name].get('volumes', []):
            if mount.get('type') == 'bind' and Path(mount.get('source', '/')).resolve() == root:
                raise RuntimeError('Montage de toute la racine Radar : examiner avant déploiement.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/opt/radar'))
    parser.add_argument('--backup-root', type=Path, default=Path('/opt/radar-deployment-backups'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Lancer avec sudo.')
    root = args.root.resolve()
    paths = json.loads(Path(__file__).with_name('paths.json').read_text())
    if any('..' in Path(path).parts or not path.startswith(('backend/', 'frontend/')) for path in paths):
        parser.error('Liste de fichiers invalide.')
    compose = ['docker', 'compose', '--project-directory', root, '-p', 'radar',
               '-f', root / 'compose.server.yml', '-f', root / 'compose.mcp.yml']
    config = json.loads(run([*compose, 'config', '--format', 'json'], capture_output=True, text=True).stdout)
    validate_config(root, config)  # Resolved secrets stay in memory, never printed.
    revision_code = "from sqlalchemy import create_engine,text; from app.core.config import settings; c=create_engine(settings.database_url).connect(); print(','.join(c.execute(text('select version_num from alembic_version')).scalars()))"
    revision = run(['docker', 'exec', 'radar-backend-1', 'python', '-c', revision_code], capture_output=True, text=True).stdout.strip()
    if revision != '056_full_credit_notes':
        parser.error(f'Révision attendue 056_full_credit_notes, reçue {revision!r}. Aucun changement.')
    extras = ['integrations/chatgpt-mfa-patch/install.py', 'integrations/chatgpt-mfa-patch/mfa-login.mjs']
    before, after = archive(BASE, paths), archive(TARGET, paths + extras)
    patch = prepare_patch(root, paths, before, after)
    if not patch:
        parser.error('Sources déjà corrigées avec une base encore en 056 : vérifier avant de continuer.')
    run(['git', 'apply', '--check', '-'], cwd=root, input=patch)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with tempfile.TemporaryDirectory(prefix='radar-mfa-stage-') as temporary:
        stage = Path(temporary)
        os.chmod(stage, 0o700)
        for directory in ['backend', 'frontend', 'chatgpt-connector']:
            shutil.copytree(root / directory, stage / directory, symlinks=True,
                ignore=shutil.ignore_patterns('node_modules', '.next', '.venv', '.git', '__pycache__', '*.log', '.mfa-patch-backups'))
        run(['git', 'apply', '-'], cwd=stage, input=patch)
        for name in extras:
            destination = stage / Path(name).name
            destination.write_bytes(after[name])
        run(['python3', stage / 'install.py', stage / 'chatgpt-connector', '--apply'])
        changed = [name for name in paths + ['chatgpt-connector/src/radar.mjs', 'chatgpt-connector/src/mfa-login.mjs']
                   if not (root / name).exists() or (root / name).read_bytes() != (stage / name).read_bytes()]
        for name in changed:
            file = root / name
            if file.is_symlink() or file.resolve() != file:
                raise RuntimeError(f'Lien non autorisé : {name}')
        print('Sources compatibles, connecteur reconnu, révision 056 confirmée.', flush=True)
        if not args.apply:
            print('Vérification terminée. Aucun service ni fichier du VPS modifié. Relancer avec --apply.')
            return
        backup = args.backup_root.resolve() / stamp
        backup.mkdir(parents=True, mode=0o700)
        os.chmod(backup.parent, 0o700)
        records, images = {}, {}
        for number, name in enumerate(changed):
            file = root / name
            record = None
            if file.exists():
                original = file.stat()
                saved = backup / f'source-{number}'
                saved.write_bytes(file.read_bytes())
                record = (saved, original)
            records[name] = record
        (backup / 'sources.json').write_text(json.dumps({name: None if value is None else {
            'backup': value[0].name, 'mode': value[1].st_mode & 0o777, 'uid': value[1].st_uid, 'gid': value[1].st_gid
        } for name, value in records.items()}, indent=2))
        overlay = {'services': {}}
        for service, directory in [('backend', 'backend'), ('frontend', 'frontend'), ('mcp', 'chatgpt-connector')]:
            info = json.loads(run(['docker', 'inspect', f'radar-{service}-1'], capture_output=True, text=True).stdout)[0]
            image, tag = info['Image'], info['Config']['Image']
            if config['services'][service].get('image', tag) != tag:
                raise RuntimeError('Tag image en cours différent de Compose : examen requis.')
            run(['docker', 'image', 'tag', image, f'radar-{service}:before-mfa-{stamp.lower()}'])
            images[tag] = image
            overlay['services'][service] = {'image': tag, 'build': {'context': str(stage / directory)}}
        (backup / 'images.json').write_text(json.dumps(images, indent=2))
        override = stage / 'build.json'
        override.write_text(json.dumps(overlay))
        stopped, migrating = False, False
        written = []
        try:
            print(f'Sauvegardes : {backup}. Construction des images avant interruption.', flush=True)
            run([*compose, '-f', override, 'build', 'backend', 'frontend', 'mcp'])
            heads = run([*compose, 'run', '--rm', '--no-deps', 'backend', 'alembic', 'heads'], capture_output=True, text=True).stdout
            if '058_revocable_sessions (head)' not in heads:
                raise RuntimeError('La nouvelle image ne contient pas la migration 058.')
            stopped = True
            run([*compose, 'stop', *SERVICES])
            for name, record in records.items():
                file = root / name
                expected = record[0].read_bytes() if record else None
                if file.is_symlink() or file.resolve() != file or (file.read_bytes() if file.exists() else None) != expected:
                    raise RuntimeError(f'Source modifiée pendant la construction : {name}. Aucun écrasement.')
            with (backup / 'database.dump').open('wb') as output:
                run([*compose, 'exec', '-T', 'postgres', 'sh', '-c',
                    'exec pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}" -Fc'], stdout=output)
                output.flush()
                os.fsync(output.fileno())
            if (backup / 'database.dump').stat().st_size < 100:
                raise RuntimeError('Sauvegarde PostgreSQL vide.')
            with (backup / 'database.dump').open('rb') as source:
                run([*compose, 'exec', '-T', 'postgres', 'pg_restore', '--list'], stdin=source, stdout=subprocess.DEVNULL)
            for name in changed:
                written.append(name)
                write_file(root / name, (stage / name).read_bytes(), records[name][1] if records[name] else None)
            migrating = True  # Never auto-restore old code after a schema/security change.
            run([*compose, 'run', '--rm', '--no-deps', 'backend', 'alembic', 'upgrade', 'head'])
            run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
            check = "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200"
            for attempt in range(30):
                healthy = subprocess.run(['docker', 'exec', 'radar-backend-1', 'python', '-c', check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
                try:
                    with urllib.request.urlopen('http://127.0.0.1:13000/login', timeout=3) as response:
                        healthy = healthy and response.status == 200
                except Exception:
                    healthy = False
                if healthy:
                    break
                if attempt == 29:
                    raise RuntimeError('Santé backend/frontend non confirmée après redémarrage.')
                time.sleep(2)
            run([*compose, 'exec', '-T', 'backend', 'alembic', 'current'])
            run([*compose, 'ps'])
            print(f'Déployé. Sauvegardes : {backup}. Reconnexion des utilisateurs et connecteurs nécessaire.', flush=True)
        except BaseException:
            if not migrating:
                for name in reversed(written):
                    record = records[name]
                    if record:
                        write_file(root / name, record[0].read_bytes(), record[1])
                    else:
                        (root / name).unlink(missing_ok=True)
                for tag, image in images.items():
                    run(['docker', 'image', 'tag', image, tag])
                if stopped:
                    run([*compose, 'up', '-d', '--no-deps', '--no-build', *SERVICES])
                print('Échec avant migration : anciennes sources et images rétablies.', flush=True)
            else:
                print(f'Échec pendant/après migration : aucun retour arrière automatique. Conserver les nouvelles images et examiner les services. Sauvegardes : {backup}', flush=True)
            raise


if __name__ == '__main__':
    main()
