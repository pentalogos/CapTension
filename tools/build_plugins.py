# -*- coding: utf-8 -*-
"""同步 core.py 到 Palette 插件，並檢查 bundle 結構。"""

import os
import plistlib
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE = os.path.join(ROOT, "plugins", "CapTension.glyphsPalette")


def sync_core():
    src = os.path.join(ROOT, "core.py")
    for bundle in (PALETTE,):
        dst = os.path.join(bundle, "Contents", "Resources", "core.py")
        shutil.copyfile(src, dst)
        print("同步 core.py →", dst)


def check_bundle(path, class_name):
    contents = os.path.join(path, "Contents")
    info_path = os.path.join(contents, "Info.plist")
    launcher = os.path.join(contents, "MacOS", "plugin")
    plugin_py = os.path.join(contents, "Resources", "plugin.py")

    with open(info_path, "rb") as f:
        info = plistlib.load(f)
    assert info["NSPrincipalClass"] == class_name, info["NSPrincipalClass"]
    assert "plugin.py" in info["PyMainFileNames"], info["PyMainFileNames"]
    assert os.path.isfile(launcher), launcher
    assert os.access(launcher, os.X_OK), launcher
    assert os.path.isfile(plugin_py), plugin_py
    with open(plugin_py, "r", encoding="utf-8") as f:
        source = f.read()
    assert ("class %s" % class_name) in source, class_name
    print("OK", os.path.basename(path), "→", class_name)


def main():
    sync_core()
    check_bundle(PALETTE, "CapTensionPalette")
    assert os.path.isfile(os.path.join(
        PALETTE, "Contents", "Resources", "vendor", "vanilla", "__init__.py"))
    assert os.path.isfile(os.path.join(
        PALETTE, "Contents", "Resources", "api.py"))
    assert os.path.isfile(os.path.join(
        PALETTE, "Contents", "Resources", "batch_instructions.py"))
    assert os.path.isfile(os.path.join(
        PALETTE, "Contents", "Resources", "i18n.py"))
    print("OK Palette vendor/vanilla + api.py + batch_instructions.py + i18n.py")
    print("全部 bundle 檢查通過。")


if __name__ == "__main__":
    main()
