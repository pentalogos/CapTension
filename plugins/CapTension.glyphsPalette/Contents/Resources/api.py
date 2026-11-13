# encoding: utf-8
"""CapTension scripting API.

可在 Glyphs 的 Macro Panel 或 Scripts 中使用。先將插件的 Resources
資料夾加入 sys.path，再 import api：

    import os, sys
    resources = os.path.expanduser(
        "~/Library/Application Support/Glyphs 4/Plugins/"
        "CapTension.glyphsPalette/Contents/Resources"
    )
    sys.path.insert(0, resources)
    import api

    font = Glyphs.font
    glyph = font.glyphs["A"]
    api.apply_glyph(glyph, 70, masters=[font.masters[0]])

所有套用/清除函式都會回傳一個統計 dict。
"""

from GlyphsApp import Glyphs

import live

DEFAULT_SHAPE = 55.23
KEY = live.PREFIX + ".value"

__all__ = [
    "DEFAULT_SHAPE",
    "master_layers",
    "targets_for_ends",
    "apply_layer",
    "clear_layer",
    "apply_glyph",
    "clear_glyph",
    "apply_font",
    "clear_font",
    "get_value",
    "set_value",
]


def _shape(value):
    value = float(value)
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return value


def _empty_result():
    return {"layers": 0, "made": 0, "removed": 0, "kept": 0}


def master_layers(glyph, masters=None):
    """回傳 glyph 在指定母版上的圖層。

    masters 可為單一 GSFontMaster、master ID、或它們的 list/tuple/set。
    None 代表該字型的所有母版。
    """
    font = getattr(glyph, "parent", None)
    if font is None:
        return []
    if masters is None:
        masters = list(font.masters)
    elif isinstance(masters, (str, bytes)):
        masters = [masters]
    elif not isinstance(masters, (list, tuple, set)):
        masters = [masters]

    layers = []
    for master in masters:
        master_id = getattr(master, "id", None) or str(master)
        layer = glyph.layerForId_(master_id)
        if layer is not None:
            layers.append(layer)
    return layers


def targets_for_ends(layer, ends=None):
    """把 "start"/"end" 轉成 update_layer 需要的 targets。

    ends=None 代表全部端點；也可以是 "start"、"end" 或它們的 list。
    """
    if ends is None:
        return None
    if isinstance(ends, str):
        ends = [ends]
    wanted = set(ends)
    return {
        (path, side)
        for path in layer.paths
        for side in ("start", "end")
        if side in wanted
    }


def apply_layer(layer, shape=DEFAULT_SHAPE, ends=None):
    """對單一圖層施加 CapTension。"""
    targets = targets_for_ends(layer, ends)
    made, removed, kept = live.update_layer(
        layer, _shape(shape), True, targets, True, True)
    return {"layers": 1, "made": made, "removed": removed, "kept": kept}


def clear_layer(layer, ends=None):
    """清除單一圖層的 CapTension，還原原生方頭。"""
    removed = live.clear_targets(layer, targets_for_ends(layer, ends))
    return {"layers": 1, "removed": removed}


def apply_glyph(glyph, shape=DEFAULT_SHAPE, masters=None, ends=None):
    """對指定字形的一或多個母版圖層施加 CapTension。"""
    result = _empty_result()
    for layer in master_layers(glyph, masters):
        part = apply_layer(layer, shape, ends)
        result["layers"] += 1
        result["made"] += part["made"]
        result["removed"] += part["removed"]
        result["kept"] += part["kept"]
    return result


def clear_glyph(glyph, masters=None, ends=None):
    """清除指定字形的一或多個母版圖層。"""
    result = {"layers": 0, "removed": 0}
    for layer in master_layers(glyph, masters):
        part = clear_layer(layer, ends)
        result["layers"] += 1
        result["removed"] += part["removed"]
    return result


def _glyphs(font, glyphs):
    if glyphs is None:
        return list(font.glyphs)
    if isinstance(glyphs, str):
        glyphs = [glyphs]
    result = []
    for item in glyphs:
        if isinstance(item, str):
            glyph = font.glyphs[item]
            if glyph is not None:
                result.append(glyph)
        else:
            result.append(item)
    return result


def apply_font(font, shape=DEFAULT_SHAPE, glyphs=None, masters=None, ends=None):
    """對整個字型（或指定字形清單）施加 CapTension。"""
    result = _empty_result()
    for glyph in _glyphs(font, glyphs):
        part = apply_glyph(glyph, shape, masters, ends)
        result["layers"] += part["layers"]
        result["made"] += part["made"]
        result["removed"] += part["removed"]
        result["kept"] += part["kept"]
    return result


def clear_font(font, glyphs=None, masters=None, ends=None):
    """清除整個字型（或指定字形清單）的 CapTension。"""
    result = {"layers": 0, "removed": 0}
    for glyph in _glyphs(font, glyphs):
        part = clear_glyph(glyph, masters, ends)
        result["layers"] += part["layers"]
        result["removed"] += part["removed"]
    return result


def get_value(font=None):
    """讀取字型的全域 CapTension 數值。"""
    font = font if font is not None else Glyphs.font
    if font is None:
        return DEFAULT_SHAPE
    try:
        raw = font.userData.get(KEY)
        if raw is not None:
            return _shape(raw)
    except Exception:
        pass
    try:
        raw = Glyphs.defaults.get(KEY)
        if raw is not None:
            return _shape(raw)
    except Exception:
        pass
    return DEFAULT_SHAPE


def set_value(value, font=None):
    """設定字型的全域 CapTension 數值。"""
    value = _shape(value)
    font = font if font is not None else Glyphs.font
    if font is not None:
        try:
            font.userData[KEY] = value
        except Exception:
            pass
    try:
        Glyphs.defaults[KEY] = value
    except Exception:
        pass
    return value
