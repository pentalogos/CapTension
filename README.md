# CapTension

CapTension 是一个 Glyphs 4 插件，让原生 Glyphs stroke 可以获得类似 FontLab 中 Cap Tension 式的可调笔端形状。

数值范围为 0–100：`0` 为尖头，`55.23` 约为正圆，`100` 为方头（带有微小圆角）。笔端形状以端点为单位套用，因此同一条路径的两端可以各自保留不同数值。笔端形状的节点数不随数值改变，使得它可以适用于可变字体。

---

## 功能

### Palette 插件

- 0–100 滑块与数值输入框（按 Enter 提交）
- `重设到圆形`：只将目前数值设回 `55.23`
- `套用到选取`：将目前数值套用到选取范围
- `清除`：移除选取范围的 CapTension
- 显示目前选取端点已套用的数值；若选取中含多个不同数值，显示「多个值」
- `复制批处理说明`：复制一份 API 使用说明，方便交给 agent 撰写 Glyphs 脚本

### 选取范围

- 在 Edit View 选取一个或多个**端点**：只处理这些端点
- 在 Edit View 选取一条或多条**开放路径**：处理这些路径的两端
- 在 Font View 选取一个或多个**字形**：只处理这些字形的当前图层
- Edit View 没有选取时：无动作
- 不跨母版、图层

---

## 界面语言

Palette 支持简体中文、繁体中文与 English，默认跟随 Glyphs 的界面语言。

如需固定语言，可在 Macro Panel 执行：

```python
Glyphs.defaults["ptlg.CapTension.language"] = "zh-Hans"   # 简体中文
# 也可设为 "zh-Hant"（繁体中文）或 "en"（English）
```

删除该键即恢复自动：

```python
del Glyphs.defaults["ptlg.CapTension.language"]
```

修改后切换一次字形或重新打开 Glyphs，Palette 与 `复制批处理说明` 的文字会一起更新。

---

## 系统需求

- macOS
- Glyphs 4

---

## 安装

1. 下载或 clone 本项目。
2. 将 `plugins/CapTension.glyphsPalette` 复制到：

   ```text
   ~/Library/Application Support/Glyphs 4/Plugins/
   ```

3. 重新启动 Glyphs 4。
4. 右侧边栏应出现 `CapTension`。

---

## 使用方式

1. 在 Edit View 开启字形。
2. 选取端点、开放路径，或在 Font View 选取字形。
3. 拖动滑块，或在数值框输入数值后按 Enter。
4. 按 `套用到选取`，将目前数值写入选取范围。
5. 如需恢复原样，按 `清除`，只清除选取范围内的 CapTension。

Palette 会显示目前选取端点已套用的数值；如果选取中含有多个不同数值，会显示「多个值」。没有已套用数值时显示「—」。

`复制批处理说明` 会把一份完整的 API 使用说明复制到剪贴板，可直接贴给 agent 作为撰写 Glyphs 脚本的规格。

---

## 脚本 API

插件提供 `api.py`，可在 Glyphs 的 Macro Panel 或 Scripts 中呼叫，对指定的字形、母版或图层施加／清除 CapTension。

先在脚本中把插件的 Resources 文件夹加入 `sys.path`：

```python
import os
import sys

resources = os.path.expanduser(
    "~/Library/Application Support/Glyphs 4/Plugins/"
    "CapTension.glyphsPalette/Contents/Resources"
)
sys.path.insert(0, resources)

import api
```

### 套用到指定字形与母版

```python
font = Glyphs.font
glyph = font.glyphs["A"]

# 只套用到第一个母版
api.apply_glyph(glyph, 70, masters=[font.masters[0]])

# 套用到该字形的所有母版
api.apply_glyph(glyph, 55.23)
```

### 套用到多个字形

```python
api.apply_font(
    Glyphs.font,
    55.23,
    glyphs=["A", "B", "C"],
    masters=[Glyphs.font.masters[0]],
)
```

### 只处理指定端点

```python
# "start"、"end"，或 ["start", "end"]
api.apply_glyph(glyph, 70, ends="start")
api.clear_glyph(glyph, ends=["start", "end"])
```

### 清除与全局数值

```python
api.clear_glyph(glyph)          # 清除该字形所有母版
api.clear_font(Glyphs.font)     # 清除整个字体

api.set_value(55.23)            # 设定全局数值
value = api.get_value()
```

### 返回值

`apply_*` 会返回类似：

```python
{"layers": 1, "made": 2, "removed": 0, "kept": 0}
```

`clear_*` 会返回：

```python
{"layers": 1, "removed": 2}
```

`masters=None` 代表该字体的全部母版；传入单一 master 或 master list 可限制范围。`ends=None` 代表两端。

---

## 运作原理

对每一个被接管的方头端点：

1. 将原生的 `lineCapStart`／`lineCapEnd` 暂时改为 **butt（平头）**。
2. 在端点 `P` 建立一个封闭的笔端形状路径，填上与 stroke 相同的颜色，并设为 locked。
3. 将每个端点的状态与数值记录在 `path.userData`。
4. 已套用的端点在拖动节点、修改宽度或颜色时会自动更新；尚未套用的端点不会被自动接管，必须按 `套用到选取`。

维护过程只读取图层；只有实际拖动滑杆、按 `套用到选取`／`清除`，或真的修改了节点、宽度、颜色时才会写入。打开文件不会自动把文件标成已编辑。

全局数值储存在字体的 `font.userData` 与 `Glyphs.defaults`；每个端点另有自己的数值。

---

## 与原生 stroke 设定的互动

- **方头端**：由插件接管；套用后 stroke 面板显示「平头」是正常现象，因为插件以平头衔接笔端形状。
- **改为圆头**：插件会在下一次更新时检测到，将该端交还给 Glyphs 原生圆头。
- **两端皆为圆头**：无动作。
- **改为平头**：由于平头正是插件写入的值，插件无法区分「用户要平头」与「插件设定的平头」，因此仍会视为接管中。若要恢复原生平头，请按 `清除`。
- **清除**：移除笔端形状并还原原生方头；只作用于选取范围。

---

## 已知限制

- 仅处理开放路径；闭合路径会跳过。
- `strokeWidth` 必须等于 `strokeHeight`，且 `strokePosition` 必须居中。
- 仅支持实色 stroke；`strokeGradient` 会跳过。
- 即时模式会在图层中加入额外的 locked 笔端形状路径。它包含 3 个 on-curve 节点与 4 个手柄，编辑时会显示；拖动节点时可能慢一个 UI 更新。
- 不会自动套用到所有母版或图层；请切换到目标图层后再套用。
- 不支持 Copy Attributes／Paste Attributes；请使用 `套用到选取` 批量施加。
- 导出时，已套用的笔端形状路径会一并输出；建议先在字体副本上测试。

---

## 开发

执行测试（不需要 Glyphs）：

```bash
python3 -m unittest discover -s tests -v
```

将 `core.py` 同步到插件 bundle，并检查 bundle 结构：

```bash
python3 tools/build_plugins.py
```

### 项目结构

```text
core.py                                  几何核心
plugins/CapTension.glyphsPalette/          Palette 插件（内含 Vanilla、api.py、i18n、批处理说明）
tests/                                   单元测试
tools/build_plugins.py                   同步与检查插件 bundle
```

### 几何模型

`core.py` 为纯 Python，实现 FontLab 的笔端形状模型：

- 端点 `P`、向外单位切线 `t`、半宽 `h`
- `X = P - n·h`、`Y = P + n·h`、`tip = P + t·h`，其中 `n = (-t.y, t.x)`
- 手柄长度 `k = h × shape / 100`
- 两段三次贝兹：`X → tip → Y`

笔端形状的节点数固定，不随数值改变。

---

## 技术信息

- Bundle ID：`ptlg.CapTension`
- UserData 命名空间：`ptlg.CapTension.*`
- 界面语言偏好键：`ptlg.CapTension.language`（可省略，省略时跟随 Glyphs）
- Palette 与脚本 API 使用同一套即时引擎；两者都会建立实际的笔端形状路径。

---

## 授权

本项目采用 MIT License，详见 [`LICENSE`](LICENSE)。
