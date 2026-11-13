# encoding: utf-8
"""API instructions copied by the Copy Batch Instructions button."""

TEXT_EN = """CapTension API - batch instructions

Add the plugin Resources folder to sys.path in a Glyphs Macro or Script:

import os
import sys

resources = os.path.expanduser(
    "~/Library/Application Support/Glyphs 4/Plugins/"
    "CapTension.glyphsPalette/Contents/Resources"
)
sys.path.insert(0, resources)

import api

Functions:

api.apply_layer(layer, shape=55.23, ends=None)
api.clear_layer(layer, ends=None)

api.apply_glyph(glyph, shape=55.23, masters=None, ends=None)
api.clear_glyph(glyph, masters=None, ends=None)

api.apply_font(font, shape=55.23, glyphs=None, masters=None, ends=None)
api.clear_font(font, glyphs=None, masters=None, ends=None)

api.set_value(value, font=None)
api.get_value(font=None)

Parameters:

- shape: 0 = pointed, 55.23 is approximately round, 100 = square.
- masters: None means all masters. You can also pass a single GSFontMaster,
  a master ID string, or a list of them.
- glyphs: None means the whole font. You can also pass a list of glyph names
  (for example ["A", "B"]) or a list of GSGlyph objects.
- ends: None means both ends. You can also pass "start", "end", or
  ["start", "end"].
- Return value is a dict, for example:
  {"layers": 1, "made": 2, "removed": 0, "kept": 0}

Examples:

font = Glyphs.font
glyph = font.glyphs["A"]

# Apply to the first master only
api.apply_glyph(glyph, 70, masters=[font.masters[0]])

# Apply to all masters of the glyph
api.apply_glyph(glyph, 55.23)

# Multiple glyphs, selected master
api.apply_font(font, 55.23, glyphs=["A", "B", "C"],
               masters=[font.masters[0]])

# Start ends only
api.apply_glyph(glyph, 70, ends="start")

# Clear
api.clear_glyph(glyph)
api.clear_font(font)

# Global value
api.set_value(55.23)
value = api.get_value()

Notes:

- The API does not use the current UI selection. Specify the glyph, master,
  or layer explicitly in the script.
- Only open paths with strokeWidth == strokeHeight, a centered stroke, and
  a solid stroke color are processed.
- Applying sets native caps to butt and adds locked cap-shape paths.
  Clearing restores native square caps.
- Test on a copy of the font first.
"""

TEXT_ZH_HANS = """CapTension API 批处理说明

在 Glyphs 的 Macro Panel 或 Scripts 中，先把插件 Resources 加入 sys.path：

import os
import sys

resources = os.path.expanduser(
    "~/Library/Application Support/Glyphs 4/Plugins/"
    "CapTension.glyphsPalette/Contents/Resources"
)
sys.path.insert(0, resources)

import api

主要函数：

api.apply_layer(layer, shape=55.23, ends=None)
api.clear_layer(layer, ends=None)

api.apply_glyph(glyph, shape=55.23, masters=None, ends=None)
api.clear_glyph(glyph, masters=None, ends=None)

api.apply_font(font, shape=55.23, glyphs=None, masters=None, ends=None)
api.clear_font(font, glyphs=None, masters=None, ends=None)

api.set_value(value, font=None)
api.get_value(font=None)

参数说明：

- shape：0 = 尖头，55.23 约为正圆，100 = 方头。
- masters：None 代表该字体的全部母版；也可传入单一 GSFontMaster、
  master ID 字符串，或它们的 list。
- glyphs：None 代表整个字体；也可传入字形名称 list（例如 ["A", "B"]）
  或 GSGlyph list。
- ends：None 代表两端；也可传入 "start"、"end" 或 ["start", "end"]。
- 返回值为 dict，例如：
  {"layers": 1, "made": 2, "removed": 0, "kept": 0}

示例：

font = Glyphs.font
glyph = font.glyphs["A"]

# 只套用到第一个母版
api.apply_glyph(glyph, 70, masters=[font.masters[0]])

# 套用到该字形的所有母版
api.apply_glyph(glyph, 55.23)

# 多个字形、指定母版
api.apply_font(font, 55.23, glyphs=["A", "B", "C"],
               masters=[font.masters[0]])

# 只处理起点
api.apply_glyph(glyph, 70, ends="start")

# 清除
api.clear_glyph(glyph)
api.clear_font(font)

# 全局数值
api.set_value(55.23)
value = api.get_value()

注意事项：

- 脚本 API 不会使用当前的 UI 选取；请在脚本中明确指定 glyph、master 或 layer。
- 只处理开放路径、strokeWidth == strokeHeight、strokePosition 居中、
  实色 stroke 的路径。
- 套用时会先把原生端点改成 butt，并加入 locked 的笔端形状路径；
  清除时还原原生方头。
- 建议先在字体副本上测试。
"""

TEXT_ZH_HANT = """CapTension API 批次處理說明

在 Glyphs 的 Macro Panel 或 Scripts 中，先把插件 Resources 加入 sys.path：

import os
import sys

resources = os.path.expanduser(
    "~/Library/Application Support/Glyphs 4/Plugins/"
    "CapTension.glyphsPalette/Contents/Resources"
)
sys.path.insert(0, resources)

import api

主要函式：

api.apply_layer(layer, shape=55.23, ends=None)
api.clear_layer(layer, ends=None)

api.apply_glyph(glyph, shape=55.23, masters=None, ends=None)
api.clear_glyph(glyph, masters=None, ends=None)

api.apply_font(font, shape=55.23, glyphs=None, masters=None, ends=None)
api.clear_font(font, glyphs=None, masters=None, ends=None)

api.set_value(value, font=None)
api.get_value(font=None)

參數說明：

- shape：0 = 尖頭，55.23 約為正圓，100 = 方頭。
- masters：None 代表該字體的全部母版；也可傳入單一 GSFontMaster、
  master ID 字串，或它們的 list。
- glyphs：None 代表整個字體；也可傳入字形名稱 list（例如 ["A", "B"]）
  或 GSGlyph list。
- ends：None 代表兩端；也可傳入 "start"、"end" 或 ["start", "end"]。
- 回傳值為 dict，例如：
  {"layers": 1, "made": 2, "removed": 0, "kept": 0}

範例：

font = Glyphs.font
glyph = font.glyphs["A"]

# 只套用到第一個母版
api.apply_glyph(glyph, 70, masters=[font.masters[0]])

# 套用到該字形的所有母版
api.apply_glyph(glyph, 55.23)

# 多個字形、指定母版
api.apply_font(font, 55.23, glyphs=["A", "B", "C"],
               masters=[font.masters[0]])

# 只處理起點
api.apply_glyph(glyph, 70, ends="start")

# 清除
api.clear_glyph(glyph)
api.clear_font(font)

# 全域數值
api.set_value(55.23)
value = api.get_value()

注意事項：

- 腳本 API 不會使用目前的 UI 選取；請在腳本中明確指定 glyph、master 或 layer。
- 只處理開放路徑、strokeWidth == strokeHeight、strokePosition 居中、
  實色 stroke 的路徑。
- 套用時會把原生端點改成 butt，並加入 locked 的筆端形狀路徑；
  清除時還原原生方頭。
- 建議先在字體副本上測試。
"""

__all__ = ["TEXT_EN", "TEXT_ZH_HANS", "TEXT_ZH_HANT"]
