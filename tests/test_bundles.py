# -*- coding: utf-8 -*-
"""檢查 Palette 插件 bundle 的結構與內容。"""

import filecmp
import os
import plistlib
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE = os.path.join(ROOT, "plugins", "CapTension.glyphsPalette")


class TestBundles(unittest.TestCase):
    def check(self, path, class_name):
        contents = os.path.join(path, "Contents")
        with open(os.path.join(contents, "Info.plist"), "rb") as f:
            info = plistlib.load(f)
        self.assertEqual(info["NSPrincipalClass"], class_name)
        self.assertIn("plugin.py", info["PyMainFileNames"])
        launcher = os.path.join(contents, "MacOS", "plugin")
        self.assertTrue(os.path.isfile(launcher))
        self.assertTrue(os.access(launcher, os.X_OK))
        plugin_py = os.path.join(contents, "Resources", "plugin.py")
        self.assertTrue(os.path.isfile(plugin_py))
        with open(plugin_py, "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("class %s" % class_name, source)

    def test_palette_bundle(self):
        self.check(PALETTE, "CapTensionPalette")
        self.assertTrue(filecmp.cmp(
            os.path.join(ROOT, "core.py"),
            os.path.join(PALETTE, "Contents", "Resources", "core.py"),
            shallow=False,
        ), "Palette bundle 的 core.py 與根目錄不同步，請跑 tools/build_plugins.py")
        self.assertTrue(os.path.isfile(os.path.join(
            PALETTE, "Contents", "Resources", "vendor", "vanilla", "__init__.py")))
        self.assertTrue(os.path.isfile(os.path.join(
            PALETTE, "Contents", "Resources", "live.py")))
        self.assertTrue(os.path.isfile(os.path.join(
            PALETTE, "Contents", "Resources", "api.py")))
        self.assertTrue(os.path.isfile(os.path.join(
            PALETTE, "Contents", "Resources", "batch_instructions.py")))
        self.assertTrue(os.path.isfile(os.path.join(
            PALETTE, "Contents", "Resources", "i18n.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
