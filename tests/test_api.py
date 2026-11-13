# -*- coding: utf-8 -*-
"""測試 CapTension 的腳本 API（不依賴 Glyphs）。"""

import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(
    ROOT, "plugins", "CapTension.glyphsPalette", "Contents", "Resources"
)
API = os.path.join(RESOURCES, "api.py")


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


class FakePath:
    def __init__(self):
        self.userData = {}


class FakeLayer:
    def __init__(self, layer_id):
        self.layerId = layer_id
        self.paths = [FakePath()]


class FakeMaster:
    def __init__(self, master_id):
        self.id = master_id


class FakeGlyph:
    def __init__(self, name, masters):
        self.name = name
        self.parent = None
        self._layers = {m.id: FakeLayer(m.id) for m in masters}

    def layerForId_(self, master_id):
        return self._layers.get(master_id)


class FakeGlyphsList:
    def __init__(self, glyphs):
        self._list = list(glyphs)
        self._by_name = {g.name: g for g in glyphs}

    def __iter__(self):
        return iter(self._list)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._by_name.get(key)
        return self._list[key]


class FakeFont:
    def __init__(self, masters, glyphs):
        self.masters = list(masters)
        self.userData = {}
        self.glyphs = FakeGlyphsList(glyphs)
        for glyph in glyphs:
            glyph.parent = self


class FakeLive:
    PREFIX = "ptlg.CapTension"

    def __init__(self):
        self.update_calls = []
        self.clear_calls = []
    def update_layer(self, layer, shape, enabled, targets, manage_new, force_butt):
        self.update_calls.append((layer, shape, enabled, targets, manage_new, force_butt))
        return (1, 0, 0)

    def clear_targets(self, layer, targets):
        self.clear_calls.append((layer, targets))
        return 1


def load_api():
    fake_glyphsapp = types.ModuleType("GlyphsApp")
    fake_glyphsapp.Glyphs = FakeGlyphs
    fake_live = FakeLive()

    names = ("GlyphsApp", "live", "api")
    old = {k: sys.modules.get(k) for k in names}
    sys.modules["GlyphsApp"] = fake_glyphsapp
    sys.modules["live"] = fake_live
    sys.modules.pop("api", None)
    try:
        spec = importlib.util.spec_from_file_location("captension_api_test", API)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in old.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod, fake_live


class TestApi(unittest.TestCase):
    def setUp(self):
        self.mod, self.live = load_api()
        self.masters = [FakeMaster("m1"), FakeMaster("m2")]
        self.glyph_a = FakeGlyph("A", self.masters)
        self.glyph_b = FakeGlyph("B", self.masters)
        self.font = FakeFont(self.masters, [self.glyph_a, self.glyph_b])
        FakeGlyphs.font = self.font
        FakeGlyphs.defaults = FakeDefaults()

    def test_master_layers(self):
        self.assertEqual(len(self.mod.master_layers(self.glyph_a)), 2)
        only = self.mod.master_layers(self.glyph_a, self.masters[0])
        self.assertEqual(len(only), 1)
        self.assertEqual(only[0].layerId, "m1")
        named = self.mod.master_layers(self.glyph_a, ["m2"])
        self.assertEqual(named[0].layerId, "m2")

    def test_targets_for_ends(self):
        layer = FakeLayer("m1")
        self.assertIsNone(self.mod.targets_for_ends(layer, None))
        start = self.mod.targets_for_ends(layer, "start")
        self.assertEqual(start, {(layer.paths[0], "start")})
        both = self.mod.targets_for_ends(layer, ["start", "end"])
        self.assertEqual(both, {
            (layer.paths[0], "start"),
            (layer.paths[0], "end"),
        })

    def test_apply_glyph_specific_master(self):
        result = self.mod.apply_glyph(self.glyph_a, 70, masters=[self.masters[0]])
        self.assertEqual(result, {"layers": 1, "made": 1, "removed": 0, "kept": 0})
        self.assertEqual(len(self.live.update_calls), 1)
        layer, shape, enabled, targets, manage_new, force_butt = self.live.update_calls[0]
        self.assertEqual(layer.layerId, "m1")
        self.assertAlmostEqual(shape, 70)
        self.assertTrue(enabled)
        self.assertIsNone(targets)
        self.assertTrue(manage_new)
        self.assertTrue(force_butt)

    def test_apply_glyph_all_masters(self):
        result = self.mod.apply_glyph(self.glyph_a, 20)
        self.assertEqual(result["layers"], 2)
        self.assertEqual(len(self.live.update_calls), 2)

    def test_apply_font_by_name(self):
        result = self.mod.apply_font(self.font, 55.23, glyphs=["A"], masters=[self.masters[1]])
        self.assertEqual(result["layers"], 1)
        self.assertEqual(self.live.update_calls[0][0].layerId, "m2")

    def test_clear_glyph(self):
        result = self.mod.clear_glyph(self.glyph_a, masters=[self.masters[0]], ends="start")
        self.assertEqual(result, {"layers": 1, "removed": 1})
        layer, targets = self.live.clear_calls[0]
        self.assertEqual(layer.layerId, "m1")
        self.assertEqual(targets, {(layer.paths[0], "start")})

    def test_get_set_value(self):
        self.assertAlmostEqual(self.mod.get_value(self.font), 55.23)
        self.mod.set_value(80, self.font)
        self.assertAlmostEqual(self.font.userData["ptlg.CapTension.value"], 80)
        self.assertAlmostEqual(self.mod.get_value(self.font), 80)
        self.assertAlmostEqual(FakeGlyphs.defaults["ptlg.CapTension.value"], 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
