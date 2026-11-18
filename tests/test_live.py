# -*- coding: utf-8 -*-
"""測試 CapTension 即時引擎（選取範圍版，不依賴 Glyphs）。"""

import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(
    ROOT, "plugins", "CapTension.glyphsPalette", "Contents", "Resources"
)
LIVE = os.path.join(RESOURCES, "live.py")


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FakeNode:
    def __init__(self, x=0, y=0, type="line", smooth=False):
        self._position = FakePoint(x, y)
        self.type = type
        self.smooth = smooth

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if isinstance(value, tuple):
            self._position = FakePoint(*value)
        else:
            self._position = value


class SpyDict(dict):
    """記錄寫入次數，用來確認維護模式不會改動文件。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self.writes.append((key, None))
        super().__delitem__(key)


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
        self.layerId = "layer-1"
        self.selection = []

    def removeShape_(self, shape):
        self.paths.remove(shape)

    def addShape_(self, shape):
        self.paths.append(shape)


def make_path(caps=(2, 2), w=30, ht=30, pos=None):
    path = FakePath()
    pts = [(167, 240), (234, 187), (330, 206), (369, 80)]
    path.nodes = [FakeNode(x, y, "line") for x, y in pts]
    path._caps = list(caps)
    path._w = w
    path._ht = ht
    path._pos = pos
    return path


def load_live():
    glyphsapp = types.ModuleType("GlyphsApp")
    glyphsapp.GSPath = FakePath
    glyphsapp.GSNode = FakeNode
    old = {k: sys.modules.get(k) for k in ("GlyphsApp", "live", "core")}
    sys.modules["GlyphsApp"] = glyphsapp
    sys.modules.pop("live", None)
    sys.modules.pop("core", None)
    if RESOURCES not in sys.path:
        sys.path.insert(0, RESOURCES)
    try:
        spec = importlib.util.spec_from_file_location("capshape_live_test", LIVE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in old.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


class TestLive(unittest.TestCase):
    def setUp(self):
        self.live = load_live()

    def cap_paths(self, layer):
        return [p for p in layer.paths if self.live.is_cap_path(p)]

    def cap_for(self, layer, path, side):
        owner = path.userData.get(self.live.OWNER_KEY)
        for cap in self.cap_paths(layer):
            if (cap.userData.get(self.live.CAP_MARK) == owner
                    and cap.userData.get(self.live.CAP_SIDE) == side):
                return cap
        return None

    def test_enable_all_square_both_ends(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, True)
        self.assertEqual((made, removed, kept), (2, 0, 0))
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 0)
        self.assertEqual(len(self.cap_paths(layer)), 2)
        self.assertAlmostEqual(path.userData[self.live.SHAPE_START], 55.23)
        self.assertAlmostEqual(path.userData[self.live.SHAPE_END], 55.23)

    def test_disable_restores_square_and_removes_caps(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 55.23, True, None, True)
        made, removed, kept = self.live.update_layer(
            layer, 55.23, False, None, False)
        self.assertEqual(made, 0)
        self.assertEqual(removed, 2)
        self.assertEqual(path.lineCapStart(), 2)
        self.assertEqual(path.lineCapEnd(), 2)
        self.assertEqual(self.cap_paths(layer), [])

    def test_both_round_does_nothing(self):
        path = make_path((1, 1))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, True)
        self.assertEqual((made, removed), (0, 0))
        self.assertEqual(path.lineCapStart(), 1)
        self.assertEqual(path.lineCapEnd(), 1)
        self.assertEqual(len(layer.paths), 1)

    def test_one_square_one_round(self):
        path = make_path((2, 1))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, True)
        self.assertEqual(made, 1)
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 1)
        self.assertEqual(len(self.cap_paths(layer)), 1)

    def test_user_changes_managed_end_to_round(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 55.23, True, None, True)
        path.attributes["lineCapStart"] = 1
        path.attributes["lineCapEnd"] = 1
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, False)
        self.assertEqual(made, 0)
        self.assertEqual(removed, 2)
        self.assertEqual(path.lineCapStart(), 1)
        self.assertEqual(path.lineCapEnd(), 1)
        self.assertFalse(path.userData[self.live.MANAGED_START])
        self.assertFalse(path.userData[self.live.MANAGED_END])

    def test_ineligible_restores_square(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 55.23, True, None, True)
        path._ht = 20
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, False)
        self.assertEqual(made, 0)
        self.assertEqual(removed, 2)
        self.assertEqual(path.lineCapStart(), 2)
        self.assertEqual(path.lineCapEnd(), 2)

    def test_selection_only_start(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        targets = {(path, "start")}
        made, removed, kept = self.live.update_layer(
            layer, 70, True, targets, True)
        self.assertEqual((made, removed, kept), (1, 0, 0))
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 2)
        self.assertIsNotNone(self.cap_for(layer, path, "start"))
        self.assertIsNone(self.cap_for(layer, path, "end"))

    def test_selection_start_then_end_keeps_first_shape(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 70, True, {(path, "start")}, True)
        self.live.update_layer(layer, 20, True, {(path, "end")}, True)
        self.assertAlmostEqual(path.userData[self.live.SHAPE_START], 70)
        self.assertAlmostEqual(path.userData[self.live.SHAPE_END], 20)
        self.assertIsNotNone(self.cap_for(layer, path, "start"))
        self.assertIsNotNone(self.cap_for(layer, path, "end"))

    def test_manage_new_false_does_not_take_new_square(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 70, True, {(path, "start")}, False)
        self.assertEqual(made, 0)
        self.assertEqual(path.lineCapStart(), 2)
        self.assertEqual(self.cap_paths(layer), [])

    def test_refresh_managed_cap_on_width_change(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 55.23, True, None, True)
        path._w = 40
        path._ht = 40
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, False)
        self.assertGreater(made, 0)
        # 兩端都應保留，且仍然是接管狀態
        self.assertEqual(len(self.cap_paths(layer)), 2)
        self.assertEqual(path.lineCapStart(), 0)

    def test_force_butt_manages_selected_butt_end(self):
        path = make_path((0, 0))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, {(path, "start")}, True, True)
        self.assertEqual(made, 1)
        self.assertEqual(path.lineCapStart(), 0)
        self.assertEqual(path.lineCapEnd(), 0)
        self.assertIsNotNone(self.cap_for(layer, path, "start"))
        self.assertIsNone(self.cap_for(layer, path, "end"))

    def test_without_force_butt_leaves_butt_end(self):
        path = make_path((0, 0))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, {(path, "start")}, True, False)
        self.assertEqual(made, 0)
        self.assertEqual(self.cap_paths(layer), [])

    def test_cap_fill_color_follows_stroke(self):
        path = make_path((2, 2))
        path.attributes["strokeColor"] = "RED"
        layer = FakeLayer([path])
        self.live.update_layer(layer, 55.23, True, None, True)
        for cap in self.cap_paths(layer):
            self.assertEqual(cap.attributes["fillColor"], "RED")

    def test_signature_changes_when_node_moves(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        sig1 = self.live.layer_signature(layer, 55.23, True)
        path.nodes[0].position = (100, 100)
        sig2 = self.live.layer_signature(layer, 55.23, True)
        self.assertNotEqual(sig1, sig2)

    def test_maintenance_on_clean_layer_writes_nothing(self):
        path = make_path((2, 2))
        path.userData = SpyDict()
        path.attributes = SpyDict()
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 55.23, True, None, False)
        self.assertEqual((made, removed, kept), (0, 0, 0))
        self.assertEqual(path.userData.writes, [])
        self.assertEqual(path.attributes.writes, [])

    def test_second_maintenance_pass_writes_nothing(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 70, True, None, True)
        caps_before = len(self.cap_paths(layer))
        path.userData = SpyDict(path.userData)
        path.attributes = SpyDict(path.attributes)
        made, removed, kept = self.live.update_layer(
            layer, 70, True, None, False)
        self.assertEqual((made, removed, kept), (0, 0, 2))
        self.assertEqual(path.userData.writes, [])
        self.assertEqual(path.attributes.writes, [])
        self.assertEqual(len(self.cap_paths(layer)), caps_before)

    def test_missing_signature_is_not_rebuilt_in_maintenance(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        self.live.update_layer(layer, 70, True, None, True)
        del path.userData[self.live.SIG_START]
        del path.userData[self.live.SIG_END]
        caps_before = len(self.cap_paths(layer))
        path.userData = SpyDict(path.userData)
        made, removed, kept = self.live.update_layer(
            layer, 70, True, None, False)
        self.assertEqual((made, removed, kept), (0, 0, 2))
        self.assertEqual(path.userData.writes, [])
        self.assertEqual(len(self.cap_paths(layer)), caps_before)

    def test_zero_shape_is_stored(self):
        path = make_path((2, 2))
        layer = FakeLayer([path])
        made, removed, kept = self.live.update_layer(
            layer, 0, True, None, True)
        self.assertEqual((made, removed, kept), (2, 0, 0))
        self.assertAlmostEqual(path.userData[self.live.SHAPE_START], 0)
        self.assertAlmostEqual(path.userData[self.live.SHAPE_END], 0)

    def test_set_cap_same_value_writes_nothing(self):
        path = make_path((2, 2))
        path.attributes = SpyDict(path.attributes)
        self.live.set_cap(path, True, 2)
        self.live.set_cap(path, False, 2)
        self.assertEqual(path.attributes.writes, [])

    def test_unique_owners_for_copied_paths(self):
        a = make_path((2, 2))
        b = make_path((2, 2))
        a.userData[self.live.OWNER_KEY] = "same"
        b.userData[self.live.OWNER_KEY] = "same"
        layer = FakeLayer([a, b])
        self.live.update_layer(layer, 55.23, True, None, True)
        self.assertNotEqual(
            a.userData[self.live.OWNER_KEY],
            b.userData[self.live.OWNER_KEY],
        )



if __name__ == "__main__":
    unittest.main(verbosity=2)
