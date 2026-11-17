"""Patch the supplied VPS connector without copying credentials or replacing OAuth.

Default: validate only. Use --apply to install, --rollback BACKUP to restore.
Requires a stopped connector while applying/restoring. No service commands run.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

MARKER = "// radar-artist-tools-patch:v1"


def check_javascript(file, node_image=None):
    if node_image:
        # Use the existing image without its service command, network, volumes,
        # environment files or grant store. Source is passed only over stdin.
        subprocess.run(['docker', 'run', '--rm', '--pull=never', '--network=none',
                        '-i', '--entrypoint', 'node', node_image,
                        '--input-type=module', '--check'], input=file.read_bytes(), check=True)
    elif shutil.which('node'):
        subprocess.run(['node', '--check', str(file)], check=True)
    else:
        raise ValueError('Node absent du VPS. Relancez avec sudo et --node-image radar-chatgpt:local pour utiliser l’image MCP existante.')


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Version du connecteur différente : ancre attendue une fois : {old[:90]}")
    return source.replace(old, new, 1)


def transform(source):
    source = source.replace('utilisez search_artists puis analyze_artist et suivez le job.',
                            'utilisez save_artist puis get_artist_profile avec job_id.')
    source = once(source, "import { z } from 'zod/v4';", "import { z } from 'zod/v4';\n"
                  "import { registerArtistTools, artistTools, artistToolNames } from './artist-tools.mjs';\n" + MARKER)
    source = once(source, "export const compiledOperations = catalog.operations.map(",
                  "export const compiledOperations = catalog.operations.filter(operation => !artistToolNames.has(operation.name)).map(")
    source = once(source, "export function registerCatalogTools(register, bridge, grantId) {",
                  "export function registerCatalogTools(register, bridge, grantId) {\n"
                  "  const allOperations = [...compiledOperations, ...artistTools];\n"
                  "  registerArtistTools(register, bridge, grantId);")
    source = once(source, "return compiledOperations.map(op =>", "return allOperations.map(op =>")
    source = once(source, "tool_count: compiledOperations.length + 19", "tool_count: allOperations.length + 19")
    source = once(source,
                  "modules: Object.fromEntries([...new Set(compiledOperations.map(op => op.family))].map(family => [family, compiledOperations.filter(op => op.family === family).length]))",
                  "modules: Object.fromEntries([...new Set(allOperations.map(op => op.family))].map(family => [family, allOperations.filter(op => op.family === family).length]))")
    return source


def atomic_write(target, data, ownership):
    fd, name = tempfile.mkstemp(prefix='.artist-patch-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(name, ownership.st_mode & 0o777)
        if os.geteuid() == 0:
            os.chown(name, ownership.st_uid, ownership.st_gid)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('connector', type=Path)
    parser.add_argument('--node-image', help='Image Docker locale contenant Node, sans téléchargement ni montage')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    root = args.connector.resolve()
    catalog = root / 'src/catalog-tools.mjs'
    tools = root / 'src/tools.mjs'
    artist = root / 'src/artist-tools.mjs'
    if not catalog.is_file() or not tools.is_file() or catalog.is_symlink() or tools.is_symlink() or artist.is_symlink():
        parser.error('Fichiers attendus absents ou liens symboliques refusés.')
    owner = catalog.stat()
    if args.rollback:
        backup = args.rollback.resolve()
        if backup.parent != root / '.artist-patch-backups' or not (backup / 'catalog-tools.mjs').is_file():
            parser.error('Utilisez un dossier de sauvegarde créé pour ce connecteur.')
        atomic_write(catalog, (backup / 'catalog-tools.mjs').read_bytes(), owner)
        if (backup / 'tools.mjs').is_file():
            atomic_write(tools, (backup / 'tools.mjs').read_bytes(), tools.stat())
        if (backup / 'artist-tools.mjs').exists():
            atomic_write(artist, (backup / 'artist-tools.mjs').read_bytes(), owner)
        else:
            artist.unlink(missing_ok=True)
        print('Fichiers restaurés. Reconstruisez et redémarrez le service MCP.')
        return
    payload = Path(__file__).with_name('artist-tools.mjs').read_bytes()
    source = catalog.read_text()
    if MARKER in source:
        if not artist.exists() or artist.read_bytes() != payload:
            parser.error('Patch déjà présent mais module différent : vérifiez les modifications locales.')
        print('Patch déjà installé ; aucun fichier modifié.')
        return
    if artist.exists():
        parser.error('Un module artist-tools.mjs existe déjà : ne pas écraser sans examen.')
    try:
        patched = transform(source).encode()
        patched_tools = once(tools.read_text(),
                             'pour les enrichir dans Radar, search_artists puis analyze_artist.',
                             'pour les enregistrer et enrichir dans Radar, utilisez save_artist puis get_artist_profile avec job_id pour suivre le résultat réel.').encode()
    except ValueError as error:
        parser.error(str(error))
    try:
        with tempfile.TemporaryDirectory(prefix='radar-artist-check-') as folder:
            for filename, contents in [('catalog-tools.mjs', patched), ('artist-tools.mjs', payload), ('tools.mjs', patched_tools)]:
                file = Path(folder) / filename
                file.write_bytes(contents)
                check_javascript(file, args.node_image)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        parser.error(f'Contrôle JavaScript échoué, aucun fichier modifié : {error}')
    print('Version reconnue et syntaxe JavaScript valide.')
    if not args.apply:
        print('Vérification seule. Arrêtez le service MCP puis relancez avec --apply pour installer.')
        return
    backup = root / '.artist-patch-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(catalog, backup / catalog.name)
    shutil.copy2(tools, backup / tools.name)
    atomic_write(artist, payload, owner)
    try:
        atomic_write(catalog, patched, owner)
        atomic_write(tools, patched_tools, tools.stat())
    except Exception:
        atomic_write(catalog, (backup / catalog.name).read_bytes(), owner)
        atomic_write(tools, (backup / tools.name).read_bytes(), tools.stat())
        artist.unlink(missing_ok=True)
        raise
    print(f'Patch installé. Sauvegarde : {backup}')
    print('Reconstruisez et redémarrez uniquement le service MCP puis rechargez ses outils dans ChatGPT.')


if __name__ == '__main__':
    main()
