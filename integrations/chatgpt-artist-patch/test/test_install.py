import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

spec = importlib.util.spec_from_file_location('artist_install', Path(__file__).resolve().parents[1] / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

# Minimal explicit source fixture; installation was also checked separately
# against the complete catalog-tools.mjs supplied by the VPS owner.
SOURCE = """import { z } from 'zod/v4';
export const compiledOperations = catalog.operations.map(operation => operation);
export function registerCatalogTools(register, bridge, grantId) {
  const search = () => { return compiledOperations.map(op => op); };
  const capability = {
    tool_count: compiledOperations.length + 19,
    modules: Object.fromEntries([...new Set(compiledOperations.map(op => op.family))].map(family => [family, compiledOperations.filter(op => op.family === family).length]))
  };
}
"""


class InstallerTests(unittest.TestCase):
    def test_docker_checks_stdin_without_network_volumes_or_host_node(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'module.mjs'
            source.write_bytes(b'export const value = 1;\n')
            with patch.object(installer.subprocess, 'run') as run:
                installer.check_javascript(source, 'radar-chatgpt:local')
            run.assert_called_once_with(
                ['docker', 'run', '--rm', '--pull=never', '--network=none', '-i',
                 '--entrypoint', 'node', 'radar-chatgpt:local', '--input-type=module', '--check'],
                input=source.read_bytes(), check=True)

    def test_missing_host_node_has_actionable_error(self):
        with patch.object(installer.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, '--node-image'):
                installer.check_javascript(Path('/not/read/on/this/path'))

    def test_native_node_is_kept_when_available(self):
        with patch.object(installer.shutil, 'which', return_value='/usr/bin/node'):
            with patch.object(installer.subprocess, 'run') as run:
                installer.check_javascript(Path('/tmp/test.mjs'))
            run.assert_called_once_with(['node', '--check', '/tmp/test.mjs'], check=True)

    def test_registers_curated_tools_and_filters_duplicate_names(self):
        result = installer.transform(SOURCE)
        self.assertIn('!artistToolNames.has(operation.name)', result)
        self.assertEqual(result.count('registerArtistTools(register, bridge, grantId);'), 1)

    def test_search_and_counts_include_curated_tools(self):
        result = installer.transform(SOURCE)
        self.assertIn('return allOperations.map(op =>', result)
        self.assertIn('tool_count: allOperations.length + 19', result)
        self.assertIn('allOperations.filter(op => op.family === family)', result)

    def test_rejects_changed_source_before_any_file_mutation(self):
        with self.assertRaises(ValueError):
            installer.transform(SOURCE.replace('compiledOperations.length + 19', 'compiledOperations.length + 20'))

    def test_rejects_ambiguous_anchor(self):
        with self.assertRaises(ValueError):
            installer.transform("import { z } from 'zod/v4';\n" + SOURCE)


if __name__ == '__main__':
    unittest.main()
