"""Run locally with unittest. All Docker/deployment operations are simulated."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).with_name('install.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTests(unittest.TestCase):
    def test_patch_adds_files_and_preserves_unrelated_local_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'backend').mkdir()
            old = ''.join(f'line {n}\n' for n in range(30)).encode()
            new = old.replace(b'line 20\n', b'secure sessions\n')
            local = old.replace(b'line 0\n', b'VPS local fix\n')
            (root / 'backend/auth.py').write_bytes(local)
            paths = ['backend/auth.py', 'backend/new.py']
            patch = deploy.prepare_patch(root, paths, {'backend/auth.py': old}, {'backend/auth.py': new, 'backend/new.py': b'new module\n'})
            deploy.run(['git', 'apply', '--check', '-'], cwd=root, input=patch)
            deploy.run(['git', 'apply', '-'], cwd=root, input=patch)
            self.assertIn(b'VPS local fix', (root / 'backend/auth.py').read_bytes())
            self.assertIn(b'secure sessions', (root / 'backend/auth.py').read_bytes())
            self.assertEqual((root / 'backend/new.py').read_bytes(), b'new module\n')

    def test_conflicting_local_change_is_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file = root / 'auth.py'
            file.write_bytes(b'unknown local login\n')
            patch = deploy.prepare_patch(root, ['auth.py'], {'auth.py': b'old login\n'}, {'auth.py': b'new login\n'})
            with self.assertRaises(subprocess.CalledProcessError):
                deploy.run(['git', 'apply', '--check', '-'], cwd=root, input=patch, stderr=subprocess.DEVNULL)
            self.assertEqual(file.read_bytes(), b'unknown local login\n')

    def test_existing_unknown_new_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'new.py').write_bytes(b'local business code\n')
            patch = deploy.prepare_patch(root, ['new.py'], {}, {'new.py': b'new security code\n'})
            with self.assertRaises(subprocess.CalledProcessError):
                deploy.run(['git', 'apply', '--check', '-'], cwd=root, input=patch, stderr=subprocess.DEVNULL)
            self.assertEqual((root / 'new.py').read_bytes(), b'local business code\n')

    def test_already_patched_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'auth.py').write_bytes(b'new\n')
            self.assertEqual(deploy.prepare_patch(root, ['auth.py'], {'auth.py': b'old\n'}, {'auth.py': b'new\n'}), b'')

    def test_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'original').write_bytes(b'secret\n')
            (root / 'auth.py').symlink_to(root / 'original')
            with self.assertRaisesRegex(RuntimeError, 'Lien'):
                deploy.prepare_patch(root, ['auth.py'], {}, {'auth.py': b'new\n'})

    def test_full_pinned_runtime_patch_applies_outside_git_checkout(self):
        # Repository is a read-only fixture provider; temporary directory has no .git.
        repo = Path(__file__).resolve().parents[2]
        paths = json.loads(Path(__file__).with_name('paths.json').read_text())
        before, after = {}, {}
        for path in paths:
            result = subprocess.run(['git', 'show', deploy.BASE + ':' + path], cwd=repo, capture_output=True)
            if result.returncode == 0:
                before[path] = result.stdout
            after[path] = subprocess.check_output(['git', 'show', deploy.TARGET + ':' + path], cwd=repo)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, data in before.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
            patch = deploy.prepare_patch(root, paths, before, after)
            deploy.run(['git', 'apply', '--check', '-'], cwd=root, input=patch)
            deploy.run(['git', 'apply', '-'], cwd=root, input=patch)
            for name in paths:
                self.assertEqual((root / name).read_bytes(), after[name], name)
            self.assertFalse((root / '.env').exists())
            self.assertFalse((root / 'compose.server.yml').exists())

    def test_unknown_worker_images_are_refused(self):
        root = Path('/opt/radar')
        services = {name: {'build': {'context': str(root / directory)}, 'image': name} for name, directory in [('backend', 'backend'), ('frontend', 'frontend'), ('mcp', 'chatgpt-connector')]}
        services.update(worker={'image': 'backend'}, scheduler={'image': 'backend'})
        deploy.validate_config(root, {'services': services})
        services['worker']['image'] = 'unrelated-worker'
        with self.assertRaisesRegex(RuntimeError, 'Image partagée'):
            deploy.validate_config(root, {'services': services})


class OrchestrationTests(unittest.TestCase):
    def exercise(self, failure=None):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        from types import SimpleNamespace
        real_run = subprocess.run
        paths = json.loads(Path(__file__).with_name('paths.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'radar'
            root.mkdir()
            before = {name: b'baseline code\n' for name in paths}
            after = {name: b'new MFA code\n' for name in paths}
            for name in before:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(before[name])
            connector = root / 'chatgpt-connector/src'
            connector.mkdir(parents=True)
            (connector / 'radar.mjs').write_bytes(b'original connector\n')
            extras = ['integrations/chatgpt-mfa-patch/install.py', 'integrations/chatgpt-mfa-patch/mfa-login.mjs']
            after.update({name: b'explicit simulation fixture\n' for name in extras})
            services = {name: {'build': {'context': str(root / directory)}, 'image': 'radar-' + name} for name, directory in [('backend', 'backend'), ('frontend', 'frontend'), ('mcp', 'chatgpt-connector')]}
            services.update(worker={'image': 'radar-backend'}, scheduler={'image': 'radar-backend'})
            calls = []
            def operation(args, **kwargs):
                args = list(map(str, args))
                calls.append(args)
                if args[:2] == ['git', 'apply']:
                    return real_run(args, check=True, **kwargs)
                if args[0] == 'python3':
                    stage = Path(args[1]).parent
                    (stage / 'chatgpt-connector/src/radar.mjs').write_bytes(b'new MFA connector\n')
                    (stage / 'chatgpt-connector/src/mfa-login.mjs').write_bytes(b'new MFA helper\n')
                elif args[:2] == ['docker', 'inspect']:
                    name = args[2].removeprefix('radar-').removesuffix('-1')
                    return SimpleNamespace(stdout=json.dumps([{'Image': 'sha256:original-' + name, 'Config': {'Image': 'radar-' + name}}]))
                elif 'config' in args:
                    return SimpleNamespace(stdout=json.dumps({'services': services}))
                elif args[:2] == ['docker', 'exec']:
                    return SimpleNamespace(stdout='056_full_credit_notes\n')
                elif 'build' in args:
                    self.assertEqual((root / paths[0]).read_bytes(), before[paths[0]])
                    if failure == 'build':
                        raise subprocess.CalledProcessError(1, args)
                elif args[-2:] == ['alembic', 'heads']:
                    return SimpleNamespace(stdout='058_revocable_sessions (head)\n')
                elif 'pg_dump' in ' '.join(args):
                    kwargs['stdout'].write(b'explicit pg_dump fixture ' * 20)
                    if failure == 'backup':
                        raise subprocess.CalledProcessError(1, args)
                elif args[-3:] == ['alembic', 'upgrade', 'head'] and failure == 'migration':
                    raise subprocess.CalledProcessError(1, args)
                return SimpleNamespace(stdout='', returncode=0)
            class Healthy:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
            argv = ['install.py', '--root', str(root), '--backup-root', str(Path(temporary) / 'backup'), '--apply']
            with patch('sys.argv', argv), patch.object(deploy.os, 'geteuid', return_value=0), patch.object(deploy, 'archive', side_effect=lambda revision, _: before if revision == deploy.BASE else after), patch.object(deploy, 'run', side_effect=operation), patch.object(deploy.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), patch.object(deploy.urllib.request, 'urlopen', return_value=Healthy()), redirect_stdout(io.StringIO()):
                if failure:
                    with self.assertRaises(subprocess.CalledProcessError):
                        deploy.main()
                else:
                    deploy.main()
            migration = [i for i, args in enumerate(calls) if args[-3:] == ['alembic', 'upgrade', 'head']]
            restorations = [args for args in calls if args[:3] == ['docker', 'image', 'tag'] and args[3].startswith('sha256:original-') and not args[4].startswith('radar-backend:before') and ':before-mfa-' not in args[4]]
            starts = [i for i, args in enumerate(calls) if 'up' in args]
            if failure in ['build', 'backup']:
                self.assertFalse(migration)
                self.assertEqual((root / paths[0]).read_bytes(), before[paths[0]])
                self.assertEqual(len(restorations), 3)
                self.assertEqual(bool(starts), failure == 'backup')
            else:
                self.assertEqual((root / paths[0]).read_bytes(), after[paths[0]])
                self.assertFalse(restorations)
                self.assertEqual(bool(starts), failure is None)
                dump = next(i for i, args in enumerate(calls) if 'pg_dump' in ' '.join(args))
                validate_dump = next(i for i, args in enumerate(calls) if 'pg_restore' in args)
                self.assertLess(dump, validate_dump)
                self.assertLess(validate_dump, migration[0])
                if starts: self.assertLess(migration[0], starts[0])

    def test_success_builds_before_downtime_backs_up_before_migration(self):
        self.exercise()

    def test_failed_build_restores_images_without_stopping_site(self):
        self.exercise('build')

    def test_failed_backup_restarts_old_site_without_migrating(self):
        self.exercise('backup')

    def test_failed_migration_never_restores_old_security_code(self):
        self.exercise('migration')


if __name__ == '__main__':
    unittest.main()
