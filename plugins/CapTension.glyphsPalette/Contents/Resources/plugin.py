# encoding: utf-8
"""CapTension Palette：即時調整 stroke 的筆端形狀。

Palette 提供滑桿、數值框、重設到圓形、套用到選取、清除與複製批次說明。
介面文字支援簡體中文、繁體中文與 English，預設跟隨 Glyphs 介面語言。
標題由 Glyphs 的 Palette 區塊標頭顯示，不再重複。
"""

from __future__ import division, print_function, unicode_literals

import os
import sys
import traceback

import objc

from GlyphsApp import (
    Glyphs, UPDATEINTERFACE, GSEditViewController, GSPath, GSNode,
)
from GlyphsApp.plugins import PalettePlugin

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
for _p in (HERE, VENDOR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vanilla import Window, Group, Slider, EditText, Button, TextBox  # noqa: E402

import i18n  # noqa: E402
import live  # noqa: E402

KEY = "ptlg.CapTension.value"
DEFAULT_SHAPE = 55.23


def clamp_shape(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return value


def format_value(value):
    return "%g" % float(value)


class CapTensionPalette(PalettePlugin):

    @objc.python_method
    def settings(self):
        self.name = "CapTension"
        self.min = 206
        self.max = 206
        self._loading = False
        self._busy = False
        self._last_signature = None
        self._font_id = None
        self._in_edit_view = False
        self._language = i18n.active_language()

        width, height = 230, 206
        self.paletteView = Window((width, height))
        self.paletteView.group = Group((0, 0, width, height))
        g = self.paletteView.group

        g.ui_slider = Slider(
            (12, 10, -12, 20),
            minValue=0,
            maxValue=100,
            value=DEFAULT_SHAPE,
            continuous=True,
            callback=self.slider_changed,
        )

        g.ui_value = EditText(
            (12, 38, 70, 22),
            format_value(DEFAULT_SHAPE),
            callback=self.value_committed,
        )

        g.ui_reset = Button(
            (92, 36, -12, 24),
            i18n.t("reset"),
            callback=self.reset,
        )

        g.ui_selected = TextBox(
            (12, 70, -12, 18),
            i18n.t("selected_prefix") + i18n.t("no_value"),
            sizeStyle="small",
        )

        g.ui_apply = Button(
            (12, 94, -12, 24),
            i18n.t("apply"),
            callback=self.apply_selection,
        )

        g.ui_clear = Button(
            (12, 132, -12, 24),
            i18n.t("clear"),
            callback=self.clear_selection,
        )

        g.ui_copy = Button(
            (12, 170, -12, 24),
            i18n.t("copy_batch"),
            callback=self.copy_batch_instructions,
        )

        self.dialog = g.getNSView()

    @objc.python_method
    def set_button_title(self, button, text):
        setter = getattr(button, "setTitle", None)
        if setter is not None:
            try:
                setter(text)
                return
            except Exception:
                traceback.print_exc()
        try:
            button.title = text
        except Exception:
            traceback.print_exc()

    @objc.python_method
    def apply_language(self):
        """把目前的介面語言重新套用到所有文字。"""
        g = self.paletteView.group
        self.set_button_title(g.ui_reset, i18n.t("reset"))
        self.set_button_title(g.ui_apply, i18n.t("apply"))
        self.set_button_title(g.ui_clear, i18n.t("clear"))
        self.set_button_title(g.ui_copy, i18n.t("copy_batch"))
        self.update_selected_values()

    @objc.python_method
    def start(self):
        Glyphs.addCallback(self.update, UPDATEINTERFACE)
        self.update(None)

    @objc.python_method
    def __del__(self):
        Glyphs.removeCallback(self.update)

    # ---------- 字體與數值 ----------

    @objc.python_method
    def current_font(self):
        wc = self.windowController()
        if wc:
            doc = wc.document()
            if doc:
                return doc.font
        return Glyphs.font

    @objc.python_method
    def font_key(self, font):
        """穩定的字體識別，避免 PyObjC 每次回傳不同 wrapper 時誤判為換字體。"""
        if font is None:
            return None
        try:
            path = font.filepath
            return (
                str(path) if path else "",
                str(font.familyName or ""),
                len(font.masters),
            )
        except Exception:
            return id(font)

    @objc.python_method
    def selected_layers(self):
        font = self.current_font()
        if font is None:
            return []
        try:
            return list(font.selectedLayers)
        except Exception:
            traceback.print_exc()
            return []

    @objc.python_method
    def path_index(self, layer, path):
        """找出 path 在 layer.paths 的索引，避免依賴 PyObjC wrapper 身分。"""
        paths = list(layer.paths)
        for i, candidate in enumerate(paths):
            if candidate is path:
                return i
        for i, candidate in enumerate(paths):
            try:
                if candidate == path:
                    return i
            except Exception:
                pass
        try:
            target = [(nd.position.x, nd.position.y) for nd in path.nodes]
        except Exception:
            return None
        for i, candidate in enumerate(paths):
            try:
                if len(candidate.nodes) != len(target):
                    continue
                if all(
                    abs(candidate.nodes[j].position.x - target[j][0]) < 0.01
                    and abs(candidate.nodes[j].position.y - target[j][1]) < 0.01
                    for j in range(len(target))
                ):
                    return i
            except Exception:
                continue
        return None

    @objc.python_method
    def selected_targets(self, layer):
        """回傳選取中的端點集合；空集合代表什麼都不做。"""
        try:
            selection = list(layer.selection)
        except Exception:
            traceback.print_exc()
            return set()
        if not selection:
            return set()

        targets = set()
        for obj in selection:
            # GSPath：有 nodes 屬性
            if hasattr(obj, "nodes"):
                if live.is_cap_path(obj):
                    continue
                index = self.path_index(layer, obj)
                if index is None:
                    continue
                targets.add((index, "start"))
                targets.add((index, "end"))
                continue

            # GSNode：有 index 與 parent
            if not hasattr(obj, "index") or not hasattr(obj, "parent"):
                continue
            path = getattr(obj, "parent", None)
            if path is None or live.is_cap_path(path):
                continue
            index = self.path_index(layer, path)
            if index is None:
                continue
            node_index = obj.index
            if node_index == 0:
                targets.add((index, "start"))
            elif node_index == len(path.nodes) - 1:
                targets.add((index, "end"))
        return targets

    @objc.python_method
    def targets_signature(self, layer, targets):
        if targets is None:
            return "all"
        return repr(sorted((str(key), side) for key, side in targets))

    @objc.python_method
    def has_selection(self):
        for layer in self.selected_layers():
            if self._in_edit_view:
                if self.selected_targets(layer):
                    return True
            elif layer.paths:
                return True
        return False

    @objc.python_method
    def selected_values(self):
        """回傳目前選取端點已套用的數值（去重、排序）。"""
        values = set()
        for layer in self.selected_layers():
            targets = (self.selected_targets(layer)
                       if self._in_edit_view else None)
            for path_index, path in enumerate(layer.paths):
                if live.is_cap_path(path):
                    continue
                ud = path.userData
                if not ud:
                    continue
                for side in ("start", "end"):
                    if (targets is not None
                            and (path_index, side) not in targets):
                        continue
                    managed_key = (live.MANAGED_START if side == "start"
                                   else live.MANAGED_END)
                    shape_key = (live.SHAPE_START if side == "start"
                                 else live.SHAPE_END)
                    if not ud.get(managed_key):
                        continue
                    raw = ud.get(shape_key)
                    if raw is None:
                        continue
                    try:
                        values.add(round(float(raw), 4))
                    except (TypeError, ValueError):
                        pass
        return sorted(values)

    @objc.python_method
    def update_selected_values(self):
        try:
            prefix = i18n.t("selected_prefix")
            values = self.selected_values()
            if not values:
                if self.has_selection():
                    text = prefix + i18n.t("not_applied")
                else:
                    text = prefix + i18n.t("no_value")
            elif len(values) == 1:
                text = prefix + format_value(values[0])
            else:
                text = prefix + i18n.t("multiple_values")
            self.paletteView.group.ui_selected.set(text)
        except Exception:
            traceback.print_exc()

    @objc.python_method
    def read_value(self, font):
        if font is not None:
            try:
                ud = font.userData
                if ud is not None:
                    raw = ud.get(KEY)
                    if raw is not None:
                        value = clamp_shape(raw)
                        if value is not None:
                            return value
            except Exception:
                print("CapTension: " + i18n.t("err_read_font_ud"))
                traceback.print_exc()
        try:
            raw = Glyphs.defaults.get(KEY)
            if raw is not None:
                value = clamp_shape(raw)
                if value is not None:
                    return value
        except Exception:
            print("CapTension: " + i18n.t("err_read_defaults"))
            traceback.print_exc()
        return DEFAULT_SHAPE

    @objc.python_method
    def save_value(self, value):
        value = clamp_shape(value)
        if value is None:
            return
        font = self.current_font()
        if font is not None:
            try:
                ud = font.userData
                raw = ud.get(KEY) if ud is not None else None
                changed = True
                if raw is not None:
                    try:
                        changed = abs(float(raw) - value) > 1e-9
                    except (TypeError, ValueError):
                        changed = True
                if changed:
                    font.userData[KEY] = value
            except Exception:
                print("CapTension: " + i18n.t("err_write_font_ud"))
                traceback.print_exc()
        try:
            raw = Glyphs.defaults.get(KEY)
            changed = True
            if raw is not None:
                try:
                    changed = abs(float(raw) - value) > 1e-9
                except (TypeError, ValueError):
                    changed = True
            if changed:
                Glyphs.defaults[KEY] = value
        except Exception:
            print("CapTension: " + i18n.t("err_write_defaults"))
            traceback.print_exc()

    # ---------- 控制項同步 ----------

    @objc.python_method
    def set_controls(self, value):
        self._loading = True
        try:
            self.paletteView.group.ui_slider.set(value)
            self.paletteView.group.ui_value.set(format_value(value))
        finally:
            self._loading = False

    # ---------- 即時套用 ----------

    @objc.python_method
    def apply_live(self, manage_new=False, force=False, force_butt=False):
        if self._busy:
            return
        # Font View 只在明確的滑桿／套用動作時處理，避免選取多個字形時
        # 每次介面重繪都掃描全部路徑。
        if not manage_new and not self._in_edit_view:
            return
        font = self.current_font()
        shape = self.read_value(font)
        layers = self.selected_layers()
        if not layers:
            return
        work = []
        signatures = []
        for layer in layers:
            if manage_new:
                targets = (self.selected_targets(layer)
                           if self._in_edit_view else None)
            else:
                # 自動維護：targets=None，但 manage_new=False 只會更新
                # 已經接管的端點，不會對新的方頭端自動施加。
                targets = None
            signatures.append(
                live.layer_signature(layer, shape, True)
                + "|targets=" + self.targets_signature(layer, targets)
            )
            work.append((layer, targets))
        combined = "\n===\n".join(signatures)
        if not force and combined == self._last_signature:
            return

        # 明確的滑桿／套用動作在 Edit View 需要選取。
        if (manage_new and self._in_edit_view and work
                and all(t == set() for _, t in work)):
            self._last_signature = combined
            print("CapTension: " + i18n.t("select_prompt"))
            return

        self._busy = True
        try:
            total_made = 0
            total_removed = 0
            total_kept = 0
            for layer, targets in work:
                if manage_new and targets == set():
                    continue
                made, removed, kept = live.update_layer(
                    layer, shape, True, targets, manage_new, force_butt)
                total_made += made
                total_removed += removed
                total_kept += kept

            # 重建後再算一次 signature，避免自己造成的變更觸發下一輪。
            signatures = []
            for layer in layers:
                if manage_new:
                    targets = (self.selected_targets(layer)
                               if self._in_edit_view else None)
                else:
                    targets = None
                signatures.append(
                    live.layer_signature(layer, shape, True)
                    + "|targets=" + self.targets_signature(layer, targets)
                )
            self._last_signature = "\n===\n".join(signatures)
            print(("CapTension: " + i18n.t("log_apply")) % (
                format_value(shape), total_made, total_removed, total_kept))
            self.update_selected_values()
        except Exception:
            print("CapTension: " + i18n.t("err_update"))
            traceback.print_exc()
        finally:
            self._busy = False

    @objc.python_method
    def update(self, sender):
        if self._loading or self._busy:
            return
        try:
            current_tab = sender.object() if sender is not None else None
            self._in_edit_view = isinstance(current_tab, GSEditViewController)
        except Exception:
            self._in_edit_view = False
        language = i18n.active_language()
        if language != self._language:
            self._language = language
            self.apply_language()

        font = self.current_font()
        font_id = self.font_key(font)

        # 切換字體時才重新載入控制項；平常不碰文字框，避免打斷輸入。
        if font_id != self._font_id:
            self._font_id = font_id
            self._last_signature = None
            self.set_controls(self.read_value(font))
            # 開啟或切換字體時只讀取，不在第一次更新就改寫圖層；
            # 否則光是打開檔案就會被標成已編輯。
            self.update_selected_values()
            return

        self.apply_live(manage_new=False)
        self.update_selected_values()

    # ---------- 回呼 ----------

    @objc.python_method
    def slider_changed(self, sender):
        if self._loading:
            return
        value = clamp_shape(sender.get())
        if value is None:
            return
        self._loading = True
        try:
            self.paletteView.group.ui_value.set(format_value(value))
        finally:
            self._loading = False
        self.save_value(value)
        self.apply_live(manage_new=True, force_butt=True)

    @objc.python_method
    def value_committed(self, sender):
        if self._loading:
            return
        value = clamp_shape(sender.get())
        if value is None:
            # 輸入不是數字：還原成目前值，不套用
            self.set_controls(self.read_value(self.current_font()))
            return
        self._loading = True
        try:
            self.paletteView.group.ui_slider.set(value)
            self.paletteView.group.ui_value.set(format_value(value))
        finally:
            self._loading = False
        self.save_value(value)
        self.apply_live(manage_new=True, force_butt=True)

    @objc.python_method
    def reset(self, sender):
        # 只重設目前數值，不套用到選取。
        # 實際套用仍由「套用到選取」執行。
        self._loading = True
        try:
            self.paletteView.group.ui_slider.set(DEFAULT_SHAPE)
            self.paletteView.group.ui_value.set(format_value(DEFAULT_SHAPE))
        finally:
            self._loading = False
        self.save_value(DEFAULT_SHAPE)

    @objc.python_method
    def apply_selection(self, sender):
        self.apply_live(manage_new=True, force=True, force_butt=True)

    @objc.python_method
    def clear_selection(self, sender):
        if self._loading or self._busy:
            return
        layers = self.selected_layers()
        if not layers:
            return

        total = 0
        skipped = False
        for layer in layers:
            targets = (self.selected_targets(layer)
                       if self._in_edit_view else None)
            if self._in_edit_view and targets == set():
                skipped = True
                continue
            total += live.clear_targets(layer, targets)

        self._last_signature = None
        if self._in_edit_view and skipped and total == 0:
            print("CapTension: " + i18n.t("select_prompt"))
        else:
            print(("CapTension: " + i18n.t("cleared")) % total)
        self.update_selected_values()

    @objc.python_method
    def copy_batch_instructions(self, sender):
        # 只複製，不顯示任何提示。
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.setString_forType_(
                i18n.batch_text(), NSPasteboardTypeString)
        except Exception:
            traceback.print_exc()

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
