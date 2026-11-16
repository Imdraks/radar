"""Deploy the reviewed frontend.patch + Nginx snippets from an unpacked bundle.

Run as root on the owner's VPS. Default is verification only; --apply deploys.
No database, secret file, OAuth store or backend service is changed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

BASE_MCP = '''location = /mcp {
    proxy_pass http://127.0.0.1:13100;
    include proxy_params;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_read_timeout 300s;
}'''
LOCATION = re.compile(r'location\s*=\s*/mcp\s*\{[^{}]*\}')


def compact(text):
    return re.sub(r'\s+', '', text)


def find_site(dump):
    """Recognize the owner's exact original block in exactly one active file."""
    candidates = []
    active_files = set(re.findall(r'^# configuration file (.+):$', dump, re.M))
    for name in active_files:
        file = Path(name).resolve()
        if not file.is_file():
            continue
        source = file.read_text()
        if 'radarapp.fr' not in source:
            continue
        for match in LOCATION.finditer(source):
            if compact(match.group()) == compact(BASE_MCP):
                candidates.append((file, source, match.span()))
    # A symlink and its real name can both occur in a dump.
    unique = {(str(file), span): (file, source, span) for file, source, span in candidates}
    if len(unique) != 1:
        raise RuntimeError('Bloc Nginx /mcp attendu absent ou ambigu. Aucun changement effectué ; transmettre le bloc actif pour examen.')
    return next(iter(unique.values()))


def patch_paths(text):
    paths = set()
    for name in re.findall(r'^\+\+\+ b/([^\t\n]+)', text, re.M):
        path = Path(name)
        if not name.startswith('frontend/src/') or '..' in path.parts:
            raise RuntimeError('Le patch contient un chemin non autorisé.')
        paths.add(path)
    if not paths or 'GIT binary patch' in text or re.search(r'^deleted file mode', text, re.M):
        raise RuntimeError('Patch vide, binaire ou supprimant des fichiers : installation refusée.')
    return sorted(paths)


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def write_preserving(file, data, fallback):
    original = file.stat() if file.exists() else fallback
    fd, tmp = tempfile.mkstemp(prefix='.radar-pages-', dir=file.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(tmp, original.st_mode & 0o777)
        os.chown(tmp, original.st_uid, original.st_gid)
        os.replace(tmp, file)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/opt/radar'))
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Exécuter avec sudo pour lire Nginx et préserver les propriétaires.')
    root, bundle = args.root.resolve(), args.bundle.resolve()
    patch = bundle / 'frontend.patch'
    mapping = bundle / 'radar-mcp-html.map.conf'
    snippet = bundle / 'radar-mcp-public.location.conf'
    paths = patch_paths(patch.read_text())
    new_directories = set()
    for relative in paths:
        file = root / relative
        if file.resolve() != file or not file.is_relative_to(root / 'frontend/src'):
            parser.error('Lien symbolique ou chemin frontend non autorisé.')
        for parent in file.parents:
            if parent == root / 'frontend/src':
                break
            if not parent.exists():
                new_directories.add(parent)
    compose = ['docker', 'compose', '-f', str(root / 'compose.server.yml')]
    config = json.loads(run([*compose, 'config', '--format', 'json'], capture_output=True, text=True).stdout)
    # Do not print the resolved Compose config: it may contain secrets.
    frontend = config['services']['frontend']
    build = frontend.get('build')
    if not isinstance(build, dict) or not build.get('context') or Path(build['context']).resolve() != root / 'frontend':
        parser.error('Contexte Docker frontend différent ; examen manuel nécessaire.')
    dump = run(['nginx', '-T'], capture_output=True, text=True).stdout
    site, old_site, span = find_site(dump)
    map_file = Path('/etc/nginx/conf.d/radar-mcp-html.conf')
    if not map_file.parent.is_dir() or map_file.is_symlink():
        parser.error('Répertoire Nginx attendu absent ou lien non autorisé.')
    if map_file.exists() and map_file.read_bytes() != mapping.read_bytes():
        parser.error('Un map Nginx différent existe déjà ; aucun écrasement.')
    patch_cmd = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-d', str(root), '-i', str(patch)]
    run([*patch_cmd, '--dry-run'])
    print('Vérification réussie : sources compatibles, frontend identifié, bloc Nginx reconnu.', flush=True)
    if not args.apply:
        print('Aucune modification. Relancer avec --apply pour déployer.')
        return

    old_image, image_tag = run(['docker', 'inspect', 'radar-frontend-1', '--format', '{{.Image}} {{.Config.Image}}'], capture_output=True, text=True).stdout.strip().split()
    backup = root / '.public-pages-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, mode=0o700)
    records = {}
    for file in [*[root / p for p in paths], site, map_file]:
        if file.exists():
            stat = file.stat()
            saved = backup / str(len(records))
            saved.write_bytes(file.read_bytes())
            records[file] = (saved, stat)
        else:
            records[file] = None
    manifest = {str(file): None if record is None else {'copy': record[0].name, 'mode': record[1].st_mode & 0o777, 'uid': record[1].st_uid, 'gid': record[1].st_gid} for file, record in records.items()}
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Sauvegarde locale : {backup}', flush=True)
    owner = (root / 'frontend/src').stat()
    nginx_changed = False
    try:
        run(patch_cmd)
        for relative in paths:
            file = root / relative
            previous = records[file]
            original = previous[1] if previous else owner
            os.chown(file, original.st_uid, original.st_gid)
            os.chmod(file, original.st_mode & 0o777 if previous else 0o644)
        for directory in new_directories:
            os.chown(directory, owner.st_uid, owner.st_gid)
        # The previous frontend container keeps serving during the build.
        run([*compose, 'build', 'frontend'])
        run([*compose, 'up', '-d', '--no-deps', '--no-build', 'frontend'])
        for attempt in range(30):
            try:
                for endpoint in ['/doc', '/mcp']:
                    with urllib.request.urlopen('http://127.0.0.1:13000' + endpoint, timeout=2) as response:
                        if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                            raise RuntimeError('Le nouveau frontend ne répond pas correctement.')
                break
            except Exception:
                if attempt == 29:
                    raise
                time.sleep(0.5)
        write_preserving(map_file, mapping.read_bytes(), site.stat())
        replacement = snippet.read_text()
        new_site = old_site[:span[0]] + replacement + old_site[span[1]:]
        write_preserving(site, new_site.encode(), site.stat())
        nginx_changed = True
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
    except BaseException:
        print('Échec : restauration des fichiers et de l’image frontend précédente.', flush=True)
        for file, record in records.items():
            if record:
                write_preserving(file, record[0].read_bytes(), record[1])
            else:
                file.unlink(missing_ok=True)
        for directory in sorted(new_directories, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()  # Only directories created here and still empty.
            except OSError:
                pass
        if nginx_changed:
            run(['nginx', '-t'])
            run(['systemctl', 'reload', 'nginx'])
        run(['docker', 'image', 'tag', old_image, image_tag])
        run([*compose, 'up', '-d', '--no-deps', '--no-build', 'frontend'])
        raise
    print('Frontend mis à jour et Nginx rechargé. Les services MCP, backend, workers et données n’ont pas été redéployés.', flush=True)
    print('Contrôler les pages publiques et appeler get_workspace dans ChatGPT.')


if __name__ == '__main__':
    main()
