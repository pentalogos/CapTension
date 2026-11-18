# MenuTitle: 清除当前/选中字形的所有端帽
# -*- coding: utf-8 -*-
"""删除当前打开或选中字形在所有母版里的 CapTension 端帽。

行为：
  - Edit View：处理当前打开的字形
  - Font View：处理所有选中的字形
  - 对该字形的所有图层（所有母版、特殊图层）和背景图层生效
  - 删除所有 CapTension 端帽
  - 清除路径上的 CapTension userData
  - 把被接管的端点还原成原生方头

这是破坏性操作，建议先备份字体。

想清理整个字体，把 TARGET_MODE 改成 "all"。
"""

from GlyphsApp import Glyphs

TARGET_MODE = "selection"   # "selection" 或 "all"

PREFIX = "ptlg.CapTension"
CAP_MARK = PREFIX + ".cap"
CAP_SIDE = PREFIX + ".capSide"
MANAGED_START = PREFIX + ".managedStart"
MANAGED_END = PREFIX + ".managedEnd"

SQUARE = 2

removed_caps = 0
restored_ends = 0
cleared_paths = 0


def user_data(path):
    try:
        return path.userData
    except Exception:
        return None


def key_string(key):
    return key if isinstance(key, str) else str(key)


def is_cap(path):
    ud = user_data(path)
    if not ud:
        return False
    try:
        return bool(ud.get(CAP_MARK))
    except Exception:
        return False


def remove_shape(layer, path):
    try:
        path.locked = False
    except Exception:
        pass
    try:
        layer.removeShape_(path)
        return True
    except Exception:
        print("无法移除路径：%r" % (path,))
        return False


def set_native_square(path, from_start):
    key = "lineCapStart" if from_start else "lineCapEnd"
    getter = getattr(path, "lineCapStart" if from_start else "lineCapEnd", None)

    def current():
        if getter is None:
            return None
        try:
            return getter()
        except Exception:
            return None

    if current() == SQUARE:
        return
    setter = getattr(
        path, "setLineCapStart_" if from_start else "setLineCapEnd_", None)
    if setter is not None:
        try:
            setter(SQUARE)
        except Exception:
            pass
    if current() == SQUARE:
        return
    try:
        path.attributes[key] = SQUARE
    except Exception:
        pass


def clean_layer(layer):
    global removed_caps, restored_ends, cleared_paths

    if layer is None:
        return

    # 删除所有端帽，包括仍然有效的端帽
    for path in list(layer.paths):
        if is_cap(path):
            if remove_shape(layer, path):
                removed_caps += 1

    # 清除状态并还原原生方头
    for path in list(layer.paths):
        if is_cap(path):
            continue
        ud = user_data(path)
        if not ud:
            continue

        changed = False

        if ud.get(MANAGED_START):
            set_native_square(path, True)
            restored_ends += 1
            changed = True
        if ud.get(MANAGED_END):
            set_native_square(path, False)
            restored_ends += 1
            changed = True

        for key in list(ud.keys()):
            if key_string(key).startswith(PREFIX):
                try:
                    del ud[key]
                    changed = True
                except Exception:
                    pass

        if changed:
            cleared_paths += 1


def current_layers(font):
    try:
        layers = list(font.selectedLayers)
    except Exception:
        layers = []
    if layers:
        return layers
    try:
        tab = font.currentTab
        layer = tab.activeLayer() if tab is not None else None
    except Exception:
        layer = None
    return [layer] if layer is not None else []


def selected_glyphs(font):
    result = []
    seen = set()
    for layer in current_layers(font):
        glyph = getattr(layer, "parent", None)
        if glyph is None:
            continue
        name = getattr(glyph, "name", None) or str(glyph)
        if name in seen:
            continue
        seen.add(name)
        result.append(glyph)
    return result


font = Glyphs.font
if font is None:
    print("没有打开的字型。")
    raise SystemExit

if TARGET_MODE == "all":
    glyphs = list(font.glyphs)
elif TARGET_MODE == "selection":
    glyphs = selected_glyphs(font)
else:
    print("TARGET_MODE 必须是 \"selection\" 或 \"all\"。")
    raise SystemExit

if not glyphs:
    print("没有打开或选中的字形。")
    print("请在 Edit View 打开字形，或在 Font View 选中字形。")
    raise SystemExit

print("处理 %d 个字形：" % len(glyphs))
for glyph in glyphs:
    before = (removed_caps, restored_ends, cleared_paths)
    try:
        layers = list(glyph.layers)
    except Exception:
        print("  跳过 %s：无法读取图层。" % getattr(glyph, "name", "?"))
        continue
    for layer in layers:
        clean_layer(layer)
        try:
            background = layer.background
        except Exception:
            background = None
        if background is not None:
            clean_layer(background)
    delta = (removed_caps - before[0],
             restored_ends - before[1],
             cleared_paths - before[2])
    if any(delta):
        print("  %s：移除端帽 %d，还原端点 %d，清理路径 %d" % (
            getattr(glyph, "name", "?"), delta[0], delta[1], delta[2]))

print("完成：")
print("  移除 CapTension 端帽：%d" % removed_caps)
print("  还原被接管的端点：%d" % restored_ends)
print("  清理路径 userData：%d" % cleared_paths)
print("请检查结果后存档。")
