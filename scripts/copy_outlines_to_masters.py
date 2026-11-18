# MenuTitle: 复制轮廓到母版…
# -*- coding: utf-8 -*-
"""复制当前字形轮廓到选中的母版，并为每个母版设置可编辑的路径属性。

使用方式：
1. 在 Edit View 打开字形，或在 Font View 选中多个字形。
2. 从 Scripts 菜单执行本脚本，或贴进 Macro Panel 执行。
3. 在弹出的窗口里勾选目标母版、调整属性值，按“复制”。
4. 勾选状态和属性值会自动记住；也可以导出／导入 JSON 预设。

复制除 CapTension 端帽之外的所有 path；端帽在目标母版重新生成。
component 与 anchor 不会复制。
来源母版会自动跳过，不会覆盖。
"""

import json
import os
import sys
import traceback

import objc
from GlyphsApp import Glyphs, GSPath, GSNode
from AppKit import NSView

try:
    from vanilla import (
        Window, Group, ScrollView, TextBox, CheckBox, EditText, Button,
        PopUpButton, HorizontalLine, VerticalLine,
    )
    from vanilla.dialogs import getFile, putFile
except ImportError:
    # 少數 Glyphs 安裝沒有把 Vanilla 放進 sys.path；退回插件自帶的版本。
    _resources = os.path.expanduser(
        "~/Library/Application Support/Glyphs 4/Plugins/"
        "CapTension.glyphsPalette/Contents/Resources"
    )
    _vendor = os.path.join(_resources, "vendor")
    if _vendor not in sys.path:
        sys.path.insert(0, _vendor)
    from vanilla import (
        Window, Group, ScrollView, TextBox, CheckBox, EditText, Button,
        PopUpButton, HorizontalLine, VerticalLine,
    )
    from vanilla.dialogs import getFile, putFile

# ============================================================
# 初始默认值
#
# 只有在“第一次打开、还没有记忆状态”时才会用到这些值。
# 之后窗口里的修改会自动记住。
#
# cap:
#   数值   = CapTension 数值（0–100）
#   None   = 不使用 CapTension
#
# native_cap:
#   "square" = 原生方头（会向外探出）
#   "butt"   = 平头
#   "round"  = 原生圆头
# ============================================================

DEFAULT_MASTER_SETTINGS = {
    "ThinSoftSquare": {"stroke": 20, "cap": 100.0, "native_cap": "square"},
    "BoldSoftSquare": {"stroke": 50, "cap": 100.0, "native_cap": "square"},
    "ThinRound":      {"stroke": 20, "cap": 55.23, "native_cap": "square"},
    "BoldRound":      {"stroke": 50, "cap": 55.23, "native_cap": "square"},
    "ThinGothic":     {"stroke": 20, "cap": None, "native_cap": "square"},
    "BoldGothic":     {"stroke": 50, "cap": None, "native_cap": "square"},
}

DEFAULT_ATTRIBUTES = [
    "strokeWidth",
    "strokeHeight",
    "strokePos",
    "lineCapStart",
    "lineCapEnd",
    "cap",
]

KNOWN_ATTRIBUTES = [
    ("strokeWidth", "笔画粗细"),
    ("strokeHeight", "笔画高度"),
    ("strokePos", "描边位置"),
    ("lineCapStart", "起点端头"),
    ("lineCapEnd", "终点端头"),
    ("cap", "CapTension"),
]

ATTRIBUTE_LABELS = dict(KNOWN_ATTRIBUTES)

# 如果端帽没有 userData 标记，按几何特征识别并排除。
# 正常情况不需要关闭。
DETECT_UNMARKED_CAPS = True

NATIVE_CAPS = {"butt": 0, "round": 1, "square": 2}

STATE_KEY = "ptlg.CapTension.copyToMasters.state"

WIDTH = 840
HEIGHT = 600
GRID_TOP = 136
BOTTOM_MARGIN = 58
NAME_WIDTH = 170
COLUMN_WIDTH = 88
GRID_PAD_X = 12


# ---------- 通用 ----------

def format_number(value):
    if value is None:
        return ""
    try:
        return "%g" % float(value)
    except (TypeError, ValueError):
        return str(value)


def parse_number(text):
    text = str(text).strip()
    if text == "":
        return None
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return None


def parse_generic(text):
    text = str(text).strip()
    low = text.lower()
    if low in ("true", "yes", "on", "是"):
        return True
    if low in ("false", "no", "off", "否"):
        return False
    number = parse_number(text)
    return text if number is None else number


def parse_cap(text):
    text = str(text or "").strip()
    if text == "" or text.lower() in ("none", "native", "无"):
        return None
    value = float(text)
    return max(0.0, min(100.0, value))


def parse_line_cap(text):
    text = str(text).strip()
    low = text.lower()
    mapping = {
        "0": 0, "1": 1, "2": 2,
        "butt": 0, "round": 1, "square": 2,
        "平头": 0, "圆头": 1, "方头": 2,
    }
    if low in mapping:
        return mapping[low]
    value = int(float(text))
    if value not in (0, 1, 2):
        raise ValueError("lineCap 只能是 0、1、2")
    return value


def parse_attribute(key, text):
    if key in ("lineCapStart", "lineCapEnd"):
        return parse_line_cap(text)
    if key in ("strokeWidth", "strokeHeight", "strokePos"):
        value = parse_number(text)
        if value is None:
            raise ValueError("需要数字")
        return value
    return parse_generic(text)


def attribute_label(key):
    return ATTRIBUTE_LABELS.get(key, key)


def seed_values(master_name, attributes):
    base = DEFAULT_MASTER_SETTINGS.get(master_name)
    if base is None:
        stroke = 50 if "bold" in master_name.lower() else 20
        cap = None
        native = "square"
    else:
        stroke = base.get("stroke", 20)
        cap = base.get("cap")
        native = base.get("native_cap", "square")

    native_value = NATIVE_CAPS.get(str(native).lower(), 2)
    values = {}
    for key in attributes:
        if key in ("strokeWidth", "strokeHeight"):
            values[key] = format_number(stroke)
        elif key == "strokePos":
            values[key] = "0"
        elif key in ("lineCapStart", "lineCapEnd"):
            values[key] = str(native_value)
        elif key == "cap":
            values[key] = "" if cap is None else format_number(cap)
        else:
            values[key] = ""
    return values


# ---------- CapTension / 字形 ----------

def load_api():
    resources = os.path.expanduser(
        "~/Library/Application Support/Glyphs 4/Plugins/"
        "CapTension.glyphsPalette/Contents/Resources"
    )
    if not os.path.isdir(resources):
        raise RuntimeError(
            "找不到 CapTension 插件的 Resources：%s\n"
            "请确认 CapTension.glyphsPalette 已安装在 Glyphs 4 的 Plugins 文件夹。"
            % resources
        )
    if resources not in sys.path:
        sys.path.insert(0, resources)
    import api
    import live
    return api, live


def copy_path(src):
    new = GSPath()
    new.closed = src.closed
    for nd in src.nodes:
        node = GSNode()
        node.type = nd.type
        node.position = (nd.position.x, nd.position.y)
        node.smooth = nd.smooth
        new.nodes.append(node)

    for key in src.attributes.keys():
        try:
            new.attributes[key] = src.attributes[key]
        except Exception:
            traceback.print_exc()

    for key, value in (src.userData or {}).items():
        key_str = key if isinstance(key, str) else str(key)
        if key_str.startswith("ptlg.CapTension"):
            continue
        try:
            new.userData[key] = value
        except Exception:
            traceback.print_exc()
    return new


def is_cap_like(path, live):
    """只排除 CapTension 端帽，其他路径全部复制。

    端帽有 userData 标记；如果标记丢失，则用几何特征兜底：
    闭合、填色、没有 stroke、7 个节点（3 on-curve + 4 off-curve）。
    """
    if live.is_cap_path(path):
        return True
    if not DETECT_UNMARKED_CAPS:
        return False
    try:
        if not path.closed:
            return False
        attrs = path.attributes
        if not attrs.get("fill"):
            return False
        stroke = attrs.get("strokeWidth")
        if stroke is not None:
            try:
                if float(stroke) != 0:
                    return False
            except (TypeError, ValueError):
                return False
        nodes = list(path.nodes)
        if len(nodes) != 7:
            return False
        # CapTension 端帽的固定结构：line + 2 off-curve + curve 重复两次
        types = [node.type for node in nodes]
        return types == [
            "line", "offcurve", "offcurve", "curve",
            "offcurve", "offcurve", "curve",
        ]
    except Exception:
        return False


def source_layers(font):
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


def source_master_id(layer):
    try:
        master_id = layer.associatedMasterId
        if master_id:
            return master_id
    except Exception:
        pass
    try:
        return layer.layerId
    except Exception:
        return None


def same_font(a, b):
    if a is b:
        return True
    try:
        return (str(a.filepath or ""), str(a.familyName or "")) == (
            str(b.filepath or ""), str(b.familyName or ""))
    except Exception:
        return False


def source_summary(font):
    layers = source_layers(font)
    names = []
    seen = set()
    for layer in layers:
        glyph = getattr(layer, "parent", None)
        name = getattr(glyph, "name", None) if glyph is not None else None
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    if not names:
        return "来源：无。请先在 Edit View 打开字形，或在 Font View 选中字形。"
    if len(names) == 1:
        layer_name = getattr(layers[0], "name", "")
        return "来源：%s / %s" % (names[0], layer_name)
    preview = "、".join(names[:6])
    if len(names) > 6:
        preview += "…"
    return "来源：%d 个选中字形（%s）" % (len(names), preview)


# ---------- 窗口 ----------

# 脚本可能在同一个 Glyphs 进程里被重复执行；PyObjC 不允许重复定义同名
# Objective-C class，所以第二次执行时直接复用上一次的 class。
try:
    FlippedDocumentView = objc.lookUpClass("CapTensionFlippedDocumentView")
except Exception:
    class CapTensionFlippedDocumentView(NSView):
        """让 ScrollView 的内容从顶部开始排列。"""

        def isFlipped(self):
            return True

    FlippedDocumentView = CapTensionFlippedDocumentView


class CopyToMastersDialog:

    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            raise RuntimeError("没有打开的字型。")

        self.state = self.load_state()
        self.sync_masters()
        self.checkboxes = {}
        self.editors = {}
        self.group_checkboxes = {}
        self.group_members = {}
        self._syncing = False
        self.content = None

        self.w = Window(
            (80, 40, WIDTH, HEIGHT), "复制轮廓到母版",
            minSize=(760, 520),
        )
        self.build()
        try:
            self.w.bind("close", self.window_will_close)
        except Exception:
            traceback.print_exc()
        self.w.open()

    # ----- 状态 -----

    def default_state(self):
        return {
            "attributes": list(DEFAULT_ATTRIBUTES),
            "groups": [],
            "masters": {},
        }

    def load_state(self):
        state = None
        try:
            raw = Glyphs.defaults.get(STATE_KEY)
        except Exception:
            raw = None
        if isinstance(raw, dict):
            state = raw
        elif isinstance(raw, str) and raw.strip():
            try:
                state = json.loads(raw)
            except Exception:
                traceback.print_exc()
                state = None

        if not isinstance(state, dict):
            state = self.default_state()

        attributes = state.get("attributes")
        if not isinstance(attributes, list):
            attributes = list(DEFAULT_ATTRIBUTES)
        attributes = [str(key) for key in attributes if str(key).strip()]
        state["attributes"] = list(dict.fromkeys(attributes))

        masters = state.get("masters")
        if not isinstance(masters, dict):
            masters = {}
        cleaned = {}
        for name, data in masters.items():
            if not isinstance(data, dict):
                continue
            values = data.get("values")
            if not isinstance(values, dict):
                values = {}
            cleaned[str(name)] = {
                "enabled": bool(data.get("enabled", True)),
                "values": {str(k): str(v) for k, v in values.items()},
            }
        state["masters"] = cleaned

        groups = state.get("groups")
        if not isinstance(groups, list):
            groups = []
        cleaned_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            name = str(group.get("name", "")).strip()
            members = group.get("members")
            if not isinstance(members, list):
                continue
            members = [str(m) for m in members if str(m).strip()]
            if name and len(members) >= 2:
                cleaned_groups.append({"name": name, "members": members})
        state["groups"] = cleaned_groups
        return state

    def sync_masters(self):
        attributes = self.state["attributes"]
        for master in self.font.masters:
            name = master.name
            if name not in self.state["masters"]:
                self.state["masters"][name] = {
                    "enabled": True,
                    "values": seed_values(name, attributes),
                }
            values = self.state["masters"][name]["values"]
            for key in attributes:
                values.setdefault(key, "")

        # 分组只保留当前字体里存在的母版；少于两个成员的分组自动解散。
        available = set(self.state["masters"].keys())
        used = set()
        groups = []
        names = set()
        for group in self.state.get("groups", []):
            name = str(group.get("name", "")).strip()
            members = []
            for member in group.get("members", []):
                member = str(member)
                if (member in available and member not in used
                        and member not in members):
                    members.append(member)
            if len(members) < 2:
                continue
            if not name or name in names:
                name = self.next_group_name(groups)
            groups.append({"name": name, "members": members})
            names.add(name)
            used.update(members)
        self.state["groups"] = groups

    def next_group_name(self, groups=None):
        existing = {
            group.get("name")
            for group in (groups if groups is not None
                          else self.state.get("groups", []))
        }
        index = 1
        while "分组 %d" % index in existing:
            index += 1
        return "分组 %d" % index

    def save_state(self):
        try:
            Glyphs.defaults[STATE_KEY] = json.dumps(
                self.state, ensure_ascii=False)
        except Exception:
            traceback.print_exc()

    def collect(self):
        if not self.checkboxes:
            return
        for name, checkbox in self.checkboxes.items():
            data = self.state["masters"].get(name)
            if data is not None:
                data["enabled"] = bool(checkbox.get())
        for (name, key), editor in self.editors.items():
            data = self.state["masters"].get(name)
            if data is not None:
                data["values"][key] = editor.get()

    # ----- 界面 -----

    def build(self):
        if self.content is not None:
            # Vanilla 不允许用同名属性替换旧控件，先从窗口移除。
            try:
                del self.w.content
            except Exception:
                traceback.print_exc()

        self.checkboxes = {}
        self.editors = {}
        # 0/0 宽高让内容跟随窗口缩放。
        self.content = Group((0, 0, 0, 0))
        c = self.content

        c.source_info = TextBox(
            (12, 10, -12, 18), source_summary(self.font), sizeStyle="small")

        attributes = self.state["attributes"]
        c.active_label = TextBox(
            (12, 32, -12, 18),
            "当前属性：" + ("、".join(attributes) if attributes else "（无）"),
            sizeStyle="small")

        c.add_popup = PopUpButton(
            (12, 56, 160, 20),
            ["%s  %s" % (label, key) for key, label in KNOWN_ATTRIBUTES],
        )
        c.custom_key = EditText((196, 56, 120, 20), "")
        c.add_button = Button(
            (324, 56, 56, 20), "添加", callback=self.add_attribute)
        c.remove_popup = PopUpButton(
            (400, 56, 170, 20), attributes if attributes else ["（无）"])
        c.remove_button = Button(
            (586, 56, 56, 20), "移除", callback=self.remove_attribute)

        all_enabled = bool(self.font.masters) and all(
            self.state["masters"].get(master.name, {}).get("enabled", True)
            for master in self.font.masters)
        c.group_line = HorizontalLine((12, 88, -12, 1))
        c.select_all = CheckBox(
            (12, 96, 64, 20), "全选",
            value=all_enabled,
            callback=self.select_all_changed,
            sizeStyle="small",
        )
        c.group_label = TextBox(
            (84, 98, 50, 18), "分组名", sizeStyle="small")
        c.group_name = EditText((136, 96, 120, 20), "")
        c.create_group = Button(
            (268, 96, 84, 20), "创建分组", callback=self.create_group)
        c.group_separator = VerticalLine((364, 100, 1, 18))
        group_names = [group["name"] for group in self.state.get("groups", [])]
        c.dissolve_popup = PopUpButton(
            (374, 96, 150, 20), group_names or ["（无分组）"])
        c.dissolve_button = Button(
            (542, 96, 64, 20), "解散", callback=self.dissolve_group)

        groups = self.state.get("groups", [])
        master_by_name = {master.name: master for master in self.font.masters}
        grouped = {
            member: group["name"]
            for group in groups
            for member in group["members"]
        }

        row_items = []
        for group in groups:
            row_items.append(("group", group))
            for member in group["members"]:
                master = master_by_name.get(member)
                if master is not None:
                    row_items.append(("master", master, True))
        for master in self.font.masters:
            if master.name not in grouped:
                row_items.append(("master", master, False))

        grid_width = (GRID_PAD_X + NAME_WIDTH + 10
                      + len(attributes) * COLUMN_WIDTH + GRID_PAD_X)
        grid_height = 30 + len(row_items) * 30 + 10
        grid = Group((0, 0, grid_width, grid_height))
        grid_view = grid.getNSView()
        grid_view.setFrame_(((0, 0), (grid_width, grid_height)))

        grid.header = TextBox(
            (GRID_PAD_X, 2, NAME_WIDTH, 18), "母版 / 分组", sizeStyle="small")
        for i, key in enumerate(attributes):
            setattr(grid, "header_%d" % i, TextBox(
                (GRID_PAD_X + NAME_WIDTH + 10 + i * COLUMN_WIDTH, 2,
                 COLUMN_WIDTH - 8, 18),
                attribute_label(key),
                sizeStyle="small",
            ))

        self.group_checkboxes = {}
        self.group_members = {}
        for row, item in enumerate(row_items):
            y = 26 + row * 30
            if item[0] == "group":
                group = item[1]
                members = list(group["members"])
                enabled = all(
                    self.state["masters"].get(name, {}).get("enabled", True)
                    for name in members
                )
                checkbox = CheckBox(
                    (GRID_PAD_X, y, NAME_WIDTH, 20),
                    "组：%s" % group["name"],
                    value=enabled,
                    callback=(
                        lambda sender, name=group["name"]:
                        self.group_toggled(name, sender)),
                    sizeStyle="small",
                )
                setattr(grid, "group_%d" % row, checkbox)
                self.group_checkboxes[group["name"]] = checkbox
                self.group_members[group["name"]] = members
                continue

            master = item[1]
            indented = item[2]
            data = self.state["masters"].get(master.name, {})
            indent = 18 if indented else 0
            checkbox = CheckBox(
                (GRID_PAD_X + indent, y, NAME_WIDTH - indent, 20),
                master.name,
                value=bool(data.get("enabled", True)),
                callback=(
                    lambda sender, name=master.name:
                    self.master_toggled(name, sender)),
                sizeStyle="small",
            )
            setattr(grid, "check_%d" % row, checkbox)
            self.checkboxes[master.name] = checkbox

            values = data.get("values", {})
            for i, key in enumerate(attributes):
                editor = EditText(
                    (GRID_PAD_X + NAME_WIDTH + 10 + i * COLUMN_WIDTH, y,
                     COLUMN_WIDTH - 16, 20),
                    str(values.get(key, "")),
                    sizeStyle="small",
                )
                setattr(grid, "value_%d_%d" % (row, i), editor)
                self.editors[(master.name, key)] = editor

        document = FlippedDocumentView.alloc().initWithFrame_(
            ((0, 0), (grid_width, grid_height)))
        document.addSubview_(grid_view)
        self.grid = grid
        self.grid_document = document

        c.scroll = ScrollView(
            (12, GRID_TOP, -12, -BOTTOM_MARGIN),
            document,
            hasHorizontalScroller=True,
            hasVerticalScroller=True,
            autohidesScrollers=True,
        )

        c.export_button = Button(
            (12, -48, 110, 22), "导出预设…", callback=self.export_preset)
        c.import_button = Button(
            (150, -48, 110, 22), "导入预设…", callback=self.import_preset)
        c.hint = TextBox(
            (282, -44, -190, 16),
            "端头 0=平 1=圆 2=方；cap 留空 = 不套用",
            sizeStyle="small")
        c.cancel_button = Button(
            (-164, -48, 64, 22), "取消", callback=self.cancel)
        c.copy_button = Button(
            (-76, -48, 64, 22), "复制", callback=self.copy)

        self.w.content = c

    def rebuild(self):
        self.build()

    # ----- 分组 / 全选 -----

    def sync_group_checks(self):
        if self._syncing:
            return
        self._syncing = True
        try:
            for name, checkbox in self.group_checkboxes.items():
                members = self.group_members.get(name, [])
                states = [
                    self.checkboxes[member].get()
                    for member in members
                    if member in self.checkboxes
                ]
                checkbox.set(bool(states) and all(states))

            states = [
                checkbox.get() for checkbox in self.checkboxes.values()
            ]
            if hasattr(self.content, "select_all"):
                self.content.select_all.set(bool(states) and all(states))
        finally:
            self._syncing = False

    def master_toggled(self, name, sender):
        if self._syncing:
            return
        data = self.state["masters"].get(name)
        if data is not None:
            data["enabled"] = bool(sender.get())
        self.sync_group_checks()

    def group_toggled(self, name, sender):
        if self._syncing:
            return
        value = bool(sender.get())
        self._syncing = True
        try:
            for member in self.group_members.get(name, []):
                checkbox = self.checkboxes.get(member)
                if checkbox is not None:
                    checkbox.set(value)
                data = self.state["masters"].get(member)
                if data is not None:
                    data["enabled"] = value
        finally:
            self._syncing = False
        self.sync_group_checks()

    def select_all_changed(self, sender):
        if self._syncing:
            return
        value = bool(sender.get())
        self._syncing = True
        try:
            for name, checkbox in self.checkboxes.items():
                checkbox.set(value)
                data = self.state["masters"].get(name)
                if data is not None:
                    data["enabled"] = value
        finally:
            self._syncing = False
        self.sync_group_checks()

    def create_group(self, sender):
        self.collect()
        members = [
            name for name, checkbox in self.checkboxes.items()
            if checkbox.get()
        ]
        if len(members) < 2:
            print("CapTension：请至少勾选两个母版，再创建分组。")
            return

        name = self.content.group_name.get().strip()
        groups = []
        for group in self.state.get("groups", []):
            remain = [
                member for member in group["members"]
                if member not in members
            ]
            if len(remain) >= 2:
                groups.append({"name": group["name"], "members": remain})

        existing = {group["name"] for group in groups}
        if not name:
            name = self.next_group_name(groups)
        else:
            base = name
            index = 2
            while name in existing:
                name = "%s %d" % (base, index)
                index += 1

        groups.append({"name": name, "members": members})
        self.state["groups"] = groups
        self.content.group_name.set("")
        self.rebuild()

    def dissolve_group(self, sender):
        self.collect()
        groups = self.state.get("groups", [])
        if not groups:
            return
        index = self.content.dissolve_popup.get()
        if index is None or index < 0 or index >= len(groups):
            return
        groups.pop(index)
        self.rebuild()

    # ----- 属性增删 -----

    def add_attribute(self, sender):
        self.collect()
        key = None
        custom = self.content.custom_key.get().strip()
        if custom:
            key = custom
        else:
            index = self.content.add_popup.get()
            if index is not None and 0 <= index < len(KNOWN_ATTRIBUTES):
                key = KNOWN_ATTRIBUTES[index][0]
        if not key:
            return
        if key in self.state["attributes"]:
            print("CapTension：属性 %s 已在列表中" % key)
            return
        self.state["attributes"].append(key)
        for data in self.state["masters"].values():
            data["values"].setdefault(key, "")
        self.content.custom_key.set("")
        self.rebuild()

    def remove_attribute(self, sender):
        self.collect()
        attributes = self.state["attributes"]
        if not attributes:
            return
        index = self.content.remove_popup.get()
        if index is None or index < 0 or index >= len(attributes):
            return
        attributes.pop(index)
        self.rebuild()

    # ----- 预设 -----

    def preset_payload(self):
        return {
            "version": 1,
            "attributes": list(self.state["attributes"]),
            "groups": list(self.state.get("groups", [])),
            "masters": self.state["masters"],
        }

    def export_preset(self, sender):
        self.collect()
        try:
            path = putFile(
                "导出 CapTension 母版预设",
                "CapTension 母版预设.json",
                fileTypes=["json"],
            )
        except Exception:
            traceback.print_exc()
            return
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.preset_payload(), f,
                          ensure_ascii=False, indent=2)
            print("CapTension：已导出预设 %s" % path)
        except Exception:
            traceback.print_exc()

    def import_preset(self, sender):
        self.collect()
        try:
            paths = getFile(
                "导入 CapTension 母版预设",
                fileTypes=["json"],
                allowsMultipleSelection=False,
            )
        except Exception:
            traceback.print_exc()
            return
        if not paths:
            return
        path = paths[0] if isinstance(paths, (list, tuple)) else paths
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            traceback.print_exc()
            return

        attributes = payload.get("attributes")
        masters = payload.get("masters")
        if not isinstance(attributes, list) or not isinstance(masters, dict):
            print("CapTension：预设格式不正确")
            return

        groups = payload.get("groups")
        cleaned_groups = []
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                name = str(group.get("name", "")).strip()
                members = group.get("members")
                if not isinstance(members, list):
                    continue
                members = [str(m) for m in members if str(m).strip()]
                if name and len(members) >= 2:
                    cleaned_groups.append(
                        {"name": name, "members": members})

        cleaned = {
            "attributes": list(dict.fromkeys(
                str(key) for key in attributes if str(key).strip())),
            "groups": cleaned_groups,
            "masters": {},
        }
        for name, data in masters.items():
            if not isinstance(data, dict):
                continue
            values = data.get("values")
            if not isinstance(values, dict):
                values = {}
            cleaned["masters"][str(name)] = {
                "enabled": bool(data.get("enabled", True)),
                "values": {str(k): str(v) for k, v in values.items()},
            }

        self.state = cleaned
        self.sync_masters()
        self.rebuild()
        print("CapTension：已导入预设 %s" % path)

    # ----- 关闭 / 复制 -----

    def window_will_close(self, sender):
        try:
            self.collect()
            self.save_state()
        except Exception:
            traceback.print_exc()

    def cancel(self, sender):
        self.collect()
        self.save_state()
        self.w.close()

    def copy(self, sender):
        self.collect()
        self.save_state()
        try:
            ok = self.perform_copy()
        except Exception:
            print("!!! 复制到母版发生错误 !!!")
            traceback.print_exc()
            return
        if ok:
            self.w.close()

    def perform_copy(self):
        font = Glyphs.font
        if font is None:
            print("没有打开的字型。")
            return False
        if not same_font(font, self.font):
            print("字体已切换，请关闭窗口后重新执行脚本。")
            return False

        self.sync_masters()
        layers = source_layers(font)
        if not layers:
            print("找不到可处理的图层。请在 Edit View 或 Font View 选取字形。")
            return False

        api, live = load_api()
        seen = set()
        glyph_count = 0
        layer_count = 0

        for source in layers:
            glyph = getattr(source, "parent", None)
            if glyph is None:
                continue
            name = getattr(glyph, "name", None) or str(glyph)
            if name in seen:
                continue
            seen.add(name)
            done = self.process_glyph(glyph, source, font, api, live)
            if done:
                glyph_count += 1
                layer_count += done

        print("全部完成：%d 个字形，%d 个母版图层。请检查后存档。" % (
            glyph_count, layer_count))
        return True

    def process_glyph(self, glyph, source, font, api, live):
        source_master = source_master_id(source)
        source_master_name = None
        for master in font.masters:
            if master.id == source_master:
                source_master_name = master.name
                break

        source_data = (self.state["masters"].get(source_master_name)
                       if source_master_name else None)
        source_enabled = bool(source_data.get("enabled", True)) \
            if source_data else False

        # 先清掉来源图层现有的端帽，这样下面读到的一定是裸路径。
        if source_enabled:
            try:
                api.clear_layer(source)
            except Exception:
                print("  警告：清除来源母版端帽失败")
                traceback.print_exc()

        all_paths = list(source.paths)
        source_paths = [p for p in all_paths
                        if not is_cap_like(p, live)]
        skipped_paths = len(all_paths) - len(source_paths)
        if skipped_paths:
            print("  跳过 %d 个 CapTension 端帽。" % skipped_paths)
        if not source_paths:
            print("跳过 %s：来源图层没有可复制的 path。" % glyph.name)
            return 0

        print("来源：%s / %s（母版：%s），path 数量 %d" % (
            glyph.name, source.name, source_master_name or "?",
            len(source_paths)))
        done = 0

        for master in font.masters:
            data = self.state["masters"].get(master.name)
            if data is None or not data.get("enabled", True):
                continue
            if source_master is not None and master.id == source_master:
                print("  跳过：%s 是来源母版，不覆盖。" % master.name)
                continue

            target = glyph.layerForId_(master.id)
            if target is None:
                print("  跳过：字形 %s 没有母版 %r 的图层" % (
                    glyph.name, master.name))
                continue

            values = data.get("values", {})
            cap_value = None
            if "cap" in self.state["attributes"]:
                try:
                    cap_value = parse_cap(values.get("cap", ""))
                except Exception:
                    print("  警告：%s 的 CapTension 数值无效，跳过 CapTension"
                          % master.name)
                    cap_value = None

            copies = [copy_path(p) for p in source_paths]
            warnings = []
            for copied in copies:
                self.apply_values(copied, values, cap_value, warnings)

            if warnings:
                for warning in warnings:
                    print("  警告：%s %s" % (master.name, warning))

            try:
                api.clear_layer(target)
            except Exception:
                print("  警告：清除 %s 的 CapTension 失败" % master.name)
                traceback.print_exc()

            for path in list(target.paths):
                try:
                    path.locked = False
                except Exception:
                    pass
                try:
                    target.removeShape_(path)
                except Exception:
                    traceback.print_exc()

            for copied in copies:
                try:
                    target.addShape_(copied)
                except Exception:
                    traceback.print_exc()

            # cap 留空时，目标路径数应与来源中“非端帽”的路径数一致。
            # 如果这里出现多余路径，多半是端帽没有被正确排除。
            if cap_value is None:
                expected = len(source_paths)
                actual = len(target.paths)
                if actual != expected:
                    print("  警告：%s 路径数 %d，预期 %d" % (
                        master.name, actual, expected))
                stray = [p for p in target.paths
                         if not live.is_cap_path(p)
                         and is_cap_like(p, live)]
                if stray:
                    print("  警告：%s 目标里出现 %d 个疑似无标记端帽" % (
                        master.name, len(stray)))

            if cap_value is not None:
                try:
                    api.apply_layer(target, cap_value)
                except Exception:
                    print("  警告：%s 套用 CapTension 失败" % master.name)
                    traceback.print_exc()

            print("  完成：%s，cap=%s" % (
                master.name,
                "native" if cap_value is None else format_number(cap_value)))
            done += 1

        # 来源母版不复制轮廓，但按它自己的设置把端帽加回来。
        if source_enabled:
            values = source_data.get("values", {})
            try:
                source_cap = parse_cap(values.get("cap", ""))
            except Exception:
                source_cap = None
            if source_cap is not None:
                try:
                    api.apply_layer(source, source_cap)
                except Exception:
                    print("  警告：来源母版重新套用 CapTension 失败")
                    traceback.print_exc()
            else:
                # cap 留空时，来源母版使用自己的原生端头设置。
                for path in source.paths:
                    for key in ("lineCapStart", "lineCapEnd"):
                        if key not in self.state["attributes"]:
                            continue
                        text = str(values.get(key, "")).strip()
                        if text == "":
                            continue
                        try:
                            path.attributes[key] = parse_line_cap(text)
                        except Exception:
                            pass

        return done

    def apply_values(self, path, values, cap_value, warnings):
        for key in self.state["attributes"]:
            if key == "cap":
                continue
            text = str(values.get(key, "")).strip()
            if text == "":
                continue
            try:
                parsed = parse_attribute(key, text)
                path.attributes[key] = parsed
            except Exception as exc:
                warnings.append("%s=%r 无法解析：%s" % (key, text, exc))

        # CapTension 需要方头作为起算点；有 cap 时强制原生端头为方头。
        if cap_value is not None:
            path.attributes["lineCapStart"] = 2
            path.attributes["lineCapEnd"] = 2


# 保持窗口对象存活，避免脚本结束后窗口被回收。
_DIALOG = None


def close_existing_dialog():
    """重复执行脚本时，先关掉上一次的窗口，避免窗口叠在一起。"""
    global _DIALOG
    if _DIALOG is None:
        return
    try:
        window = _DIALOG.w
        # 已经关闭过的 Window 不能再 close；只在还活着时关闭。
        if getattr(window, "_window", None) is not None:
            window.close()
    except Exception:
        traceback.print_exc()
    _DIALOG = None


def main():
    global _DIALOG
    try:
        close_existing_dialog()
        _DIALOG = CopyToMastersDialog()
        print("CapTension：复制窗口已打开")
    except Exception:
        print("!!! 复制到母版脚本发生错误 !!!")
        traceback.print_exc()
        raise


main()
