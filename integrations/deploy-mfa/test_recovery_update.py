"""Recovery updater checks: local file copies, mocked Docker and no real e-mail."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('recovery_update', Path(__file__).with_name('update_password_recovery.py'))
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class PatchTests(unittest.TestCase):
    def test_complete_pinned_patch_creates_every_new_runtime_file(self):
        repo = Path(__file__).resolve().parents[2]
        def reference(candidates, tree):
            for ref in candidates:
                result = subprocess.run(['git', 'rev-parse', ref + '^{tree}'], cwd=repo, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip() == tree:
                    return ref
            self.fail('Pinned fixture missing: fetch deployment baselines.')
        base = reference([update.BASE, '7193191'], 'bda3205d21f2ab5ccf1ac29a7aa7bd2f9744bc2e')
        target = reference([update.TARGET, '36b1aab'], 'dfb4395cb71d35095d4cc9d500857d93b4a22133')
        before, after = {}, {}
        for name in update.FILES:
            result = subprocess.run(['git', 'show', base + ':' + name], cwd=repo, capture_output=True)
            if result.returncode == 0: before[name] = result.stdout
            after[name] = subprocess.check_output(['git', 'show', target + ':' + name], cwd=repo)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in before.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(content)
            correction = update.make_patch(root, before, after)
            update.run(['git', 'apply', '--check', '-'], cwd=root, input=correction, stderr=subprocess.DEVNULL)
            update.run(['git', 'apply', '-'], cwd=root, input=correction, stderr=subprocess.DEVNULL)
            for name in update.FILES:
                self.assertEqual((root / name).read_bytes(), after[name], name)
            self.assertEqual(update.make_patch(root, before, after), b'')

    def test_unknown_new_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ['backend/new.py']
            (root / 'backend').mkdir()
            (root / names[0]).write_bytes(b'custom business code\n')
            with patch.object(update, 'FILES', names), patch.object(update, 'NEW_FILES', set(names)):
                with self.assertRaisesRegex(RuntimeError, 'contenu non reconnu'):
                    update.make_patch(root, {}, {names[0]: b'new security code\n'})
            self.assertEqual((root / names[0]).read_bytes(), b'custom business code\n')


class DeploymentTests(unittest.TestCase):
    def exercise(self, failure=None):
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'radar'
            root.mkdir()
            names = ['backend/old.py', 'frontend/old.tsx', 'frontend/src/app/forgot-password/page.tsx']
            added = {names[-1]}
            before = {name: b'value = "original"\n' for name in names[:-1]}
            after = {name: b'value = "updated"\n' for name in names}
            for name, content in before.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(content)
            services = {service: {'build': {'context': str(root / service)}, 'image': 'radar-' + service} for service in ['backend', 'frontend']}
            services.update(worker={'image': 'radar-backend'}, scheduler={'image': 'radar-backend'})
            calls, starts = [], []
            def operation(args, **kwargs):
                args = list(map(str, args)); calls.append(args)
                if args[:2] == ['git', 'apply']: return real_run(args, check=True, **kwargs)
                if args[:2] == ['docker', 'exec']: return SimpleNamespace(stdout='058_revocable_sessions\n')
                if 'config' in args: return SimpleNamespace(stdout=json.dumps({'services': services}))
                if args[:2] == ['docker', 'inspect']:
                    name = args[2].removeprefix('radar-').removesuffix('-1')
                    return SimpleNamespace(stdout=json.dumps([{'Image': 'sha256:old-' + name, 'Config': {'Image': 'radar-' + name}}]))
                if 'build' in args:
                    self.assertEqual((root / names[0]).read_bytes(), before[names[0]])
                    self.assertFalse((root / names[-1]).exists())
                    if failure == 'build': raise subprocess.CalledProcessError(1, args)
                    if failure == 'concurrent': (root / names[0]).write_bytes(b'operator edit\n')
                if 'up' in args:
                    starts.append(args)
                    if failure == 'restart' and len(starts) == 1: raise subprocess.CalledProcessError(1, args)
                if failure == 'worker' and any('Worker de récupération' in value for value in args):
                    raise subprocess.CalledProcessError(1, args)
                return SimpleNamespace(stdout='', returncode=0)
            class Healthy:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
            argv = ['update_password_recovery.py', '--apply', '--root', str(root), '--backup-root', str(Path(temporary) / 'backups')]
            with patch('sys.argv', argv), patch.object(update.os, 'geteuid', return_value=0), patch.object(update, 'FILES', names), patch.object(update, 'NEW_FILES', added), patch.object(update, 'fetch_files', side_effect=lambda ref: before if ref == update.BASE else after), patch.object(update, 'run', side_effect=operation), patch.object(update.urllib.request, 'urlopen', return_value=Healthy()), patch.object(update.time, 'sleep'), redirect_stdout(io.StringIO()):
                if failure:
                    with self.assertRaises((RuntimeError, subprocess.CalledProcessError)): update.main()
                else: update.main()
            self.assertFalse(any('alembic' in args or 'pg_dump' in args for args in calls))
            stops = [i for i, args in enumerate(calls) if 'stop' in args]
            build = next(i for i, args in enumerate(calls) if 'build' in args)
            restores = [args for args in calls if args[:3] == ['docker', 'image', 'tag'] and ':before-password-recovery-' not in args[-1]]
            if failure:
                self.assertEqual(len(restores), 2)
                self.assertFalse((root / names[-1]).exists())
                self.assertEqual((root / names[0]).read_bytes(), b'operator edit\n' if failure == 'concurrent' else before[names[0]])
                if failure in ['build', 'concurrent']:
                    self.assertFalse(stops); self.assertFalse(starts)
                else: self.assertEqual(len(starts), 2)
            else:
                self.assertFalse(restores)
                self.assertLess(build, stops[0])
                for name in names: self.assertEqual((root / name).read_bytes(), after[name])
                manifest = json.loads(next((Path(temporary) / 'backups').glob('*/sources.json')).read_text())
                self.assertIsNone(manifest[names[-1]])
                self.assertTrue(any('Worker de récupération' in value for args in calls for value in args))

    def test_success_creates_routes_after_build_and_checks_worker(self): self.exercise()
    def test_failed_build_does_not_stop_the_site(self): self.exercise('build')
    def test_failed_restart_removes_new_files_and_restores_old_sources(self): self.exercise('restart')
    def test_unready_worker_prevents_false_success_and_rolls_back(self): self.exercise('worker')
    def test_concurrent_edit_is_preserved(self): self.exercise('concurrent')


if __name__ == '__main__': unittest.main()
