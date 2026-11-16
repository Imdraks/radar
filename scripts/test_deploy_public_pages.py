"""Deployment regression using a disposable file tree and explicit service fixtures."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deploy_public_pages', Path(__file__).with_name('deploy_public_pages.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

SOURCE_PATCH = '''diff --git a/frontend/src/old.tsx b/frontend/src/old.tsx
--- a/frontend/src/old.tsx
+++ b/frontend/src/old.tsx
@@ -1 +1 @@
-old
+updated
diff --git a/frontend/src/doc/new.tsx b/frontend/src/doc/new.tsx
new file mode 100644
--- /dev/null
+++ b/frontend/src/doc/new.tsx
@@ -0,0 +1 @@
+created
'''


class DeploymentTests(unittest.TestCase):
    def test_rejects_non_frontend_paths_and_deletions(self):
        for source in ['+++ b/.env\n', '+++ b/frontend/src/../../secret\n', SOURCE_PATCH + '\ndeleted file mode 100644\n']:
            with self.assertRaises(RuntimeError):
                deploy.patch_paths(source)

    def test_recognizes_whitespace_but_refuses_unknown_nginx_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder) / 'site'
            site.write_text('server_name radarapp.fr;\n' + deploy.BASE_MCP.replace('    ', '\t'))
            self.assertEqual(deploy.find_site(f'# configuration file {site}:\n')[0], site)
            site.write_text(site.read_text().replace('proxy_buffering off;', 'proxy_buffering off; proxy_set_header X-Extra keep;'))
            with self.assertRaises(RuntimeError):
                deploy.find_site(f'# configuration file {site}:\n')

    def test_refuses_ambiguous_active_sites(self):
        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder) / name for name in ['one', 'two']]
            for file in files:
                file.write_text('server_name radarapp.fr;\n' + deploy.BASE_MCP)
            with self.assertRaises(RuntimeError):
                deploy.find_site(''.join(f'# configuration file {file}:\n' for file in files))

    def scenario(self, apply=False, fail_build=False, fail_nginx=False):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, bundle = base / 'radar', base / 'bundle'
            (root / 'frontend/src').mkdir(parents=True)
            bundle.mkdir()
            target = root / 'frontend/src/old.tsx'
            target.write_text('old\n')
            (root / 'compose.server.yml').write_text('# explicit test fixture\n')
            (bundle / 'frontend.patch').write_text(SOURCE_PATCH)
            (bundle / 'radar-mcp-html.map.conf').write_text('# explicit map fixture\n')
            (bundle / 'radar-mcp-public.location.conf').write_text('location = /mcp { # fixture replacement\n}\n')
            site = base / 'site.conf'
            original = 'server_name radarapp.fr;\n' + deploy.BASE_MCP + '\nlocation = /token { # keep OAuth fixture\n}\n'
            site.write_text(original)
            map_file = base / 'conf.d/radar-mcp-html.conf'
            map_file.parent.mkdir()
            calls = []
            original_run = subprocess.run

            def command(argv, **kwargs):
                calls.append(argv)
                if argv[0] == 'patch':
                    return original_run(argv, **kwargs, stdout=subprocess.DEVNULL)
                if argv[-3:] == ['config', '--format', 'json']:
                    return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({'services': {'frontend': {'build': {'context': str(root / 'frontend')}}}}))
                if argv == ['nginx', '-T']:
                    return subprocess.CompletedProcess(argv, 0, stdout=f'# configuration file {site}:\n')
                if argv[:2] == ['docker', 'inspect']:
                    return subprocess.CompletedProcess(argv, 0, stdout='sha256:old_image radar-frontend:latest\n')
                if argv[-2:] == ['build', 'frontend'] and fail_build:
                    raise subprocess.CalledProcessError(1, argv)
                if argv == ['nginx', '-t'] and fail_nginx and site.read_text() != original:
                    raise subprocess.CalledProcessError(1, argv)
                return subprocess.CompletedProcess(argv, 0)

            def mapped_path(value):
                return map_file if str(value) == '/etc/nginx/conf.d/radar-mcp-html.conf' else Path(value)

            response = contextlib.nullcontext(type('Response', (), {'status': 200, 'headers': {'Content-Type': 'text/html'}})())
            argv = ['deploy.py', '--root', str(root), '--bundle', str(bundle)] + (['--apply'] if apply else [])
            with patch.object(deploy, 'Path', side_effect=mapped_path), patch.object(deploy, 'run', side_effect=command), patch.object(deploy.os, 'geteuid', return_value=0), patch.object(deploy.os, 'chown'), patch.object(deploy.urllib.request, 'urlopen', return_value=response), patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
                if fail_build or fail_nginx:
                    with self.assertRaises(subprocess.CalledProcessError):
                        deploy.main()
                else:
                    deploy.main()
            if not apply or fail_build or fail_nginx:
                self.assertEqual(target.read_text(), 'old\n')
                self.assertFalse((root / 'frontend/src/doc/new.tsx').exists())
                self.assertEqual(site.read_text(), original)
                self.assertFalse(map_file.exists())
            else:
                self.assertEqual(target.read_text(), 'updated\n')
                self.assertEqual((root / 'frontend/src/doc/new.tsx').read_text(), 'created\n')
                self.assertIn('keep OAuth fixture', site.read_text())
                self.assertTrue(map_file.exists())
                self.assertIn(['systemctl', 'reload', 'nginx'], calls)
            if fail_build or fail_nginx:
                self.assertIn(['docker', 'image', 'tag', 'sha256:old_image', 'radar-frontend:latest'], calls)
            for call in calls:
                self.assertNotIn('backend', call)
                self.assertNotIn('mcp', call)
                self.assertNotIn('down', call)

    def test_dry_run_changes_no_files_or_services(self):
        self.scenario()

    def test_success_only_updates_frontend_and_known_nginx_block(self):
        self.scenario(apply=True)

    def test_build_failure_restores_files_and_previous_image(self):
        self.scenario(apply=True, fail_build=True)

    def test_nginx_validation_failure_restores_both_files_and_previous_image(self):
        self.scenario(apply=True, fail_nginx=True)


if __name__ == '__main__':
    unittest.main()
