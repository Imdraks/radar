import importlib.util
from pathlib import Path
import unittest

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
