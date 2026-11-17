"""Local copies and simulated Docker only; no production services are contacted."""
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

spec = importlib.util.spec_from_file_location('password_update', Path(__file__).with_name('update_password_prompt.py'))
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class PatchTests(unittest.TestCase):
    def test_real_runtime_patch_preserves_local_edits_without_git_checkout(self):
        repo = Path(__file__).resolve().parents[2]
        def equivalent_ref(candidates, expected_tree):
            for ref in candidates:
                result = subprocess.run(['git', 'rev-parse', ref + '^{tree}'], cwd=repo, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip() == expected_tree:
                    return ref
            self.fail('Pinned fixture tree unavailable; fetch the deployment baseline commits.')
        base = equivalent_ref([update.BASE, '7193191'], 'bda3205d21f2ab5ccf1ac29a7aa7bd2f9744bc2e')
        target = equivalent_ref([update.TARGET, '7ac7c07'], 'ae2ba25732db77eeeb538bdd01217d4242a34417')
        before = {name: subprocess.check_output(['git', 'show', base + ':' + name], cwd=repo) for name in update.FILES}
        after = {name: subprocess.check_output(['git', 'show', target + ':' + name], cwd=repo) for name in update.FILES}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, source in before.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(source)
            local = root / update.FILES[1]
            local.write_bytes(local.read_bytes() + b'\n# unrelated VPS fix\n')
            correction = update.make_patch(root, before, after)
            update.run(['git', 'apply', '--check', '-'], cwd=root, input=correction)
            update.run(['git', 'apply', '-'], cwd=root, input=correction)
            for name in update.FILES:
                expected = after[name] + (b'\n# unrelated VPS fix\n' if name == update.FILES[1] else b'')
                self.assertEqual((root / name).read_bytes(), expected)
            self.assertFalse(update.make_patch(root, {n: (root / n).read_bytes() for n in update.FILES}, {n: (root / n).read_bytes() for n in update.FILES}))

    def test_unknown_conflict_and_symlink_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = {name: b'old = 1\n' for name in update.FILES}
            after = {name: b'new = 2\n' for name in update.FILES}
            for name in update.FILES:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'unknown = 3\n')
            correction = update.make_patch(root, before, after)
            with self.assertRaises(subprocess.CalledProcessError):
                update.run(['git', 'apply', '--check', '-'], cwd=root, input=correction, stderr=subprocess.DEVNULL)
            file = root / update.FILES[0]
            file.unlink()
            file.symlink_to(root / update.FILES[1])
            with self.assertRaisesRegex(RuntimeError, 'lien refusé'):
                update.make_patch(root, before, after)


class UpdateTests(unittest.TestCase):
    def exercise(self, failure=None):
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'radar'
            root.mkdir()
            before = {name: b'value = "original"\n' for name in update.FILES}
            after = {name: b'value = "updated"\n' for name in update.FILES}
            for name in update.FILES:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(before[name])
            services = {service: {'build': {'context': str(root / service)}, 'image': 'radar-' + service} for service in ['backend', 'frontend']}
            services.update(worker={'image': 'radar-backend'}, scheduler={'image': 'radar-backend'})
            calls, starts = [], []
            def operation(args, **kwargs):
                args = list(map(str, args))
                calls.append(args)
                if args[:2] == ['git', 'apply']:
                    return real_run(args, check=True, **kwargs)
                if 'config' in args:
                    return SimpleNamespace(stdout=json.dumps({'services': services}))
                if args[:2] == ['docker', 'inspect']:
                    name = args[2].removeprefix('radar-').removesuffix('-1')
                    return SimpleNamespace(stdout=json.dumps([{'Image': 'sha256:original-' + name, 'Config': {'Image': 'radar-' + name}}]))
                if 'build' in args:
                    self.assertEqual((root / update.FILES[0]).read_bytes(), before[update.FILES[0]])
                    if failure == 'build':
                        raise subprocess.CalledProcessError(1, args)
                    if failure == 'concurrent':
                        (root / update.FILES[0]).write_bytes(b'operator changed the file\n')
                if 'up' in args:
                    starts.append(args)
                    if failure == 'restart' and len(starts) == 1:
                        raise subprocess.CalledProcessError(1, args)
                return SimpleNamespace(stdout='', returncode=0)
            class Healthy:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
            argv = ['update_password_prompt.py', '--apply', '--root', str(root), '--backup-root', str(Path(temporary) / 'backup')]
            with patch('sys.argv', argv), patch.object(update.os, 'geteuid', return_value=0), patch.object(update, 'download', side_effect=lambda rev, name: (before if rev == update.BASE else after)[name]), patch.object(update, 'run', side_effect=operation), patch.object(update.urllib.request, 'urlopen', return_value=Healthy()), redirect_stdout(io.StringIO()):
                if failure:
                    with self.assertRaises((subprocess.CalledProcessError, RuntimeError)):
                        update.main()
                else:
                    update.main()
            self.assertFalse(any('alembic' in args or 'pg_dump' in args for args in calls))
            stops = [i for i, args in enumerate(calls) if 'stop' in args]
            build = next(i for i, args in enumerate(calls) if 'build' in args)
            restored = [args for args in calls if args[:3] == ['docker', 'image', 'tag'] and ':before-password-prompt-' not in args[-1]]
            if failure:
                self.assertEqual(len(restored), 2)
                if failure == 'concurrent':
                    self.assertEqual((root / update.FILES[0]).read_bytes(), b'operator changed the file\n')
                else:
                    for name in update.FILES:
                        self.assertEqual((root / name).read_bytes(), before[name])
                if failure in ['build', 'concurrent']:
                    self.assertFalse(stops)
                    self.assertFalse(starts)
                else:
                    self.assertEqual(len(starts), 2)
            else:
                self.assertFalse(restored)
                self.assertLess(build, stops[0])
                for name in update.FILES:
                    self.assertEqual((root / name).read_bytes(), after[name])
                manifests = list((Path(temporary) / 'backup').glob('*/sources.json'))
                self.assertEqual(len(manifests), 1)

    def test_success(self): self.exercise()
    def test_failed_build_preserves_running_site(self): self.exercise('build')
    def test_failed_restart_restores_sources_and_images(self): self.exercise('restart')
    def test_concurrent_operator_edit_is_preserved(self): self.exercise('concurrent')


if __name__ == '__main__':
    unittest.main()
