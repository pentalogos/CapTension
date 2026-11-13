# -*- coding: utf-8 -*-
"""用假的 GlyphsApp / vanilla 測試 Palette 插件的 UI 與數值邏輯。"""

import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(
    ROOT, "plugins", "CapTension.glyphsPalette", "Contents", "Resources"
)
PLUGIN = os.path.join(RESOURCES, "plugin.py")
KEY = "ptlg.CapTension.value"


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeNode:
    def __init__(self, x=0, y=0, type="line", smooth=False):
        self._position = FakePoint(x, y)
        self.type = type
        self.smooth = smooth
        self.parent = None
        self.index = 0

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if isinstance(value, tuple):
            self._position = FakePoint(*value)
        else:
            self._position = value


class FakePath:
    def __init__(self):
        self.nodes = []
        self.closed = False
        self.attributes = {}
        self.userData = {}
        self.locked = False
        self._w = 30
        self._ht = 30
        self._pos = None
        self._caps = [2, 2]

    def strokeWidth(self):
        return self._w

    def strokeHeight(self):
        return self._ht

    def strokePosition(self):
        return self._pos

    def lineCapStart(self):
        return self.attributes.get("lineCapStart", self._caps[0])

    def lineCapEnd(self):
        return self.attributes.get("lineCapEnd", self._caps[1])


class FakeLayer:
    def __init__(self, paths):
        self.paths = list(paths)
        self.selection = []
        self.layerId = "layer-1"

    def removeShape_(self, shape):
        self.paths.remove(shape)

    def addShape_(self, shape):
        self.paths.append(shape)


class FakeDefaults:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data.get(key)

    def __setitem__(self, key, value):
        self.data[key] = value


class FakeGlyphs:
    font = None
    defaults = FakeDefaults()
    language = "zh-Hans"

    @staticmethod
    def localize(table):
        lang = FakeGlyphs.language
        if lang in table:
            return table[lang]
        for key in (lang.split("-")[0], "en"):
            if key in table:
                return table[key]
        return next(iter(table.values()))

    @staticmethod
    def addCallback(fn, event):
        pass

    @staticmethod
    def removeCallback(fn):
        pass


class FakeSlider:
    def __init__(self, posSize, minValue=0, maxValue=100, value=50,
                 continuous=True, callback=None, **kwargs):
        self.value = value
        self.callback = callback

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeText:
    def __init__(self, posSize, text="", callback=None, **kwargs):
        self.text = text
        self.callback = callback

    def get(self):
        return self.text

    def set(self, value):
        self.text = value


class FakeButton:
    def __init__(self, posSize, title="", callback=None, **kwargs):
        self.title = title
        self.callback = callback


class FakeGroup:
    def __init__(self, posSize):
        self.posSize = posSize
        self._nsview = object()

    def getNSView(self):
        return self._nsview


class FakeWindow:
    def __init__(self, posSize):
        self.posSize = posSize
        self.group = None


def make_fake_modules():
    glyphsapp = types.ModuleType("GlyphsApp")
    glyphsapp.Glyphs = FakeGlyphs
    glyphsapp.UPDATEINTERFACE = "UPDATEINTERFACE"
    glyphsapp.GSPath = FakePath
    glyphsapp.GSNode = FakeNode

    class GSEditViewController:
        pass

    glyphsapp.GSEditViewController = GSEditViewController

    plugins = types.ModuleType("GlyphsApp.plugins")

    class PalettePlugin:
        def windowController(self):
            return getattr(self, "_wc", None)

    plugins.PalettePlugin = PalettePlugin
    glyphsapp.plugins = plugins

    objc = types.ModuleType("objc")
    objc.python_method = lambda f: f

    vanilla = types.ModuleType("vanilla")
    vanilla.Window = FakeWindow
    vanilla.Group = FakeGroup
    vanilla.Slider = FakeSlider
    vanilla.EditText = FakeText
    vanilla.TextBox = FakeText
    vanilla.Button = FakeButton

    return glyphsapp, plugins, objc, vanilla


def load_plugin():
    glyphsapp, plugins, objc, vanilla = make_fake_modules()
    names = ("GlyphsApp", "GlyphsApp.plugins", "objc", "vanilla",
             "live", "core", "i18n", "batch_instructions")
    old = {k: sys.modules.get(k) for k in names}
    sys.modules["GlyphsApp"] = glyphsapp
    sys.modules["GlyphsApp.plugins"] = plugins
    sys.modules["objc"] = objc
    sys.modules["vanilla"] = vanilla
    sys.modules.pop("live", None)
    sys.modules.pop("core", None)
    try:
        spec = importlib.util.spec_from_file_location("capshape_palette_test", PLUGIN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in old.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


class TestPalettePlugin(unittest.TestCase):
    def setUp(self):
        self.mod = load_plugin()
        FakeGlyphs.defaults = FakeDefaults()
        FakeGlyphs.language = "zh-Hans"
        self.font = types.SimpleNamespace(
            userData={}, familyName="Test Family", selectedLayers=[]
        )
        FakeGlyphs.font = self.font
        doc = types.SimpleNamespace(font=self.font)
        wc = types.SimpleNamespace(document=lambda: doc)
        self.plugin = self.mod.CapTensionPalette()
        self.plugin._wc = wc
        self.plugin.settings()
        self.plugin.start()
        self.g = self.plugin.paletteView.group

    def make_layer(self):
        path = FakePath()
        pts = [(167, 240), (234, 187), (330, 206), (369, 80)]
        path.nodes = [FakeNode(x, y, "line") for x, y in pts]
        for i, node in enumerate(path.nodes):
            node.parent = path
            node.index = i
        layer = FakeLayer([path])
        self.font.selectedLayers = [layer]
        return layer, path

    def test_selected_targets_from_node_path_and_nothing(self):
        layer, path = self.make_layer()
        layer.selection = [path.nodes[0]]
        self.assertEqual(self.plugin.selected_targets(layer), {(0, "start")})
        layer.selection = [path]
        self.assertEqual(
            self.plugin.selected_targets(layer),
            {(0, "start"), (0, "end")},
        )
        layer.selection = []
        self.assertEqual(self.plugin.selected_targets(layer), set())
        layer.selection = [path.nodes[1]]
        self.assertEqual(self.plugin.selected_targets(layer), set())

    def test_font_change_update_is_read_only(self):
        calls = []
        self.plugin.apply_live = lambda **kwargs: calls.append(kwargs)
        self.plugin._font_id = None
        self.plugin.update(None)
        self.assertEqual(calls, [])

    def test_apply_live_selection_persists_shapes(self):
        layer, path = self.make_layer()
        self.plugin._in_edit_view = True
        self.font.userData[KEY] = 70
        layer.selection = [path]
        self.plugin.apply_live(manage_new=True, force=True)
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 0)
        caps = [p for p in layer.paths
                if p.userData.get(self.mod.live.CAP_MARK)]
        self.assertEqual(len(caps), 2)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_START], 70)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_END], 70)

        # 只選起點，套用 20；終點應保留 70
        layer.selection = [path.nodes[0]]
        self.font.userData[KEY] = 20
        self.plugin.apply_live(manage_new=True, force=True)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_START], 20)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_END], 70)
        caps = [p for p in layer.paths
                if p.userData.get(self.mod.live.CAP_MARK)]
        self.assertEqual(len(caps), 2)

    def test_clear_selection_only_targeted_end(self):
        layer, path = self.make_layer()
        self.plugin._in_edit_view = True
        self.font.userData[KEY] = 70
        layer.selection = [path]
        self.plugin.apply_live(manage_new=True, force=True)
        self.assertEqual(len([p for p in layer.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 2)

        layer.selection = [path.nodes[0]]
        self.plugin.clear_selection(None)
        self.assertEqual(path.lineCapStart(), 2)
        self.assertEqual(path.lineCapEnd(), 0)
        self.assertFalse(path.userData[self.mod.live.MANAGED_START])
        self.assertTrue(path.userData[self.mod.live.MANAGED_END])
        self.assertEqual(len([p for p in layer.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 1)

    def test_clear_without_selection_does_nothing(self):
        layer, path = self.make_layer()
        self.plugin._in_edit_view = True
        self.font.userData[KEY] = 70
        layer.selection = [path]
        self.plugin.apply_live(manage_new=True, force=True)
        layer.selection = []
        self.plugin.clear_selection(None)
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 0)
        self.assertEqual(len([p for p in layer.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 2)

    def test_clear_font_view_does_not_touch_other_layer(self):
        layer1, path1 = self.make_layer()
        layer2, path2 = self.make_layer()
        self.mod.live.update_layer(layer1, 70, True, None, True)
        self.mod.live.update_layer(layer2, 70, True, None, True)
        self.plugin._in_edit_view = False
        self.font.selectedLayers = [layer1]
        self.plugin.clear_selection(None)
        self.assertEqual(path1.lineCapStart(), 2)
        self.assertEqual(path1.lineCapEnd(), 2)
        self.assertEqual(path2.lineCapStart(), 0)
        self.assertEqual(path2.lineCapEnd(), 0)
        self.assertEqual(len([p for p in layer1.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 0)
        self.assertEqual(len([p for p in layer2.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 2)

    def test_reset_only_changes_value_not_selection(self):
        layer, path = self.make_layer()
        self.plugin._in_edit_view = True
        self.font.userData[KEY] = 70
        layer.selection = [path]
        self.plugin.apply_live(manage_new=True, force=True)
        caps = [p for p in layer.paths
                if p.userData.get(self.mod.live.CAP_MARK)]
        self.assertEqual(len(caps), 2)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_START], 70)

        self.plugin.reset(None)
        self.assertAlmostEqual(self.g.ui_slider.get(), 55.23)
        self.assertEqual(self.g.ui_value.get(), "55.23")
        self.assertAlmostEqual(self.font.userData[KEY], 55.23)
        # 選取中的端帽不應被重設動作改動
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 0)
        self.assertAlmostEqual(path.userData[self.mod.live.SHAPE_START], 70)
        self.assertEqual(len([p for p in layer.paths
                              if p.userData.get(self.mod.live.CAP_MARK)]), 2)

    def test_selected_values_display(self):
        layer, path = self.make_layer()
        self.plugin._in_edit_view = True
        layer.selection = [path]
        self.plugin.update_selected_values()
        self.assertEqual(self.g.ui_selected.get(), "目前选取：未套用")

        self.font.userData[KEY] = 70
        self.plugin.apply_live(manage_new=True, force=True)
        self.assertEqual(self.plugin.selected_values(), [70.0])
        self.plugin.update_selected_values()
        self.assertEqual(self.g.ui_selected.get(), "目前选取：70")

        # 起點改成 20，終點保留 70 → 顯示多個值
        layer.selection = [path.nodes[0]]
        self.font.userData[KEY] = 20
        self.plugin.apply_live(manage_new=True, force=True)
        layer.selection = [path]
        self.assertEqual(self.plugin.selected_values(), [20.0, 70.0])
        self.plugin.update_selected_values()
        self.assertEqual(self.g.ui_selected.get(), "目前选取：多个值")

        # 兩端同為 40 → 只顯示 40
        self.font.userData[KEY] = 40
        self.plugin.apply_live(manage_new=True, force=True)
        self.assertEqual(self.plugin.selected_values(), [40.0])
        self.plugin.update_selected_values()
        self.assertEqual(self.g.ui_selected.get(), "目前选取：40")

        # 沒有選取 → 不顯示數值
        layer.selection = []
        self.plugin.update_selected_values()
        self.assertEqual(self.g.ui_selected.get(), "目前选取：—")
        self.assertEqual(self.g.ui_copy.title, "复制批处理说明")
        text = self.mod.i18n.batch_text()
        self.assertIn("api.apply_glyph", text)
        self.assertIn("masters=None", text)
        self.assertIn("ends=None", text)

    # ---------- 多語系 ----------

    def make_settings_plugin(self):
        plugin = self.mod.CapTensionPalette()
        plugin._wc = self.plugin._wc
        plugin.settings()
        return plugin

    def test_language_selection(self):
        FakeGlyphs.language = "zh-Hant"
        g = self.make_settings_plugin().paletteView.group
        self.assertEqual(g.ui_apply.title, "套用到選取")
        self.assertEqual(g.ui_selected.get(), "目前選取：—")

        FakeGlyphs.language = "zh-Hans"
        g = self.make_settings_plugin().paletteView.group
        self.assertEqual(g.ui_apply.title, "套用到选取")
        self.assertEqual(g.ui_selected.get(), "目前选取：—")

        FakeGlyphs.defaults[self.mod.i18n.LANGUAGE_KEY] = "en"
        g = self.make_settings_plugin().paletteView.group
        self.assertEqual(g.ui_apply.title, "Apply to Selection")
        self.assertEqual(g.ui_selected.get(), "Selected: —")

    def test_batch_text_in_three_languages(self):
        i18n = self.mod.i18n
        key = i18n.LANGUAGE_KEY
        FakeGlyphs.defaults[key] = "zh-Hans"
        self.assertIn("批处理说明", i18n.batch_text())
        FakeGlyphs.defaults[key] = "zh-Hant"
        self.assertIn("批次處理說明", i18n.batch_text())
        FakeGlyphs.defaults[key] = "en"
        self.assertIn("batch instructions", i18n.batch_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
