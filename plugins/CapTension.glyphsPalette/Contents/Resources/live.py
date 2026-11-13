# encoding: utf-8
"""CapTension 即時引擎（選取範圍版）。

做法：不破壞原生 stroke。對每一個「方頭」端點：
  1. 把該端的原生 lineCap 暫時改成 butt（平頭），筆畫本體剛好停在端點 P。
  2. 另外建立一個封閉的「筆端形狀」路徑，底邊貼在 P 的橫截面上。
  3. 把筆端形狀填上與 stroke 相同的顏色，疊在筆畫上。

選取範圍：
  - targets=None：處理 layer 內所有合格的端點（目前圖層模式）。
  - targets={(path, "start"/"end"), ...}：只處理指定端點。

每個端點會記住自己套用的 shape 值，所以選 A 端拖滑桿不會改到 B 端。
"""

import traceback
import uuid

from GlyphsApp import GSPath, GSNode

import core

PREFIX = "ptlg.CapTension"
OWNER_KEY = PREFIX + ".owner"
CAP_MARK = PREFIX + ".cap"
CAP_SIDE = PREFIX + ".capSide"
MANAGED_START = PREFIX + ".managedStart"
MANAGED_END = PREFIX + ".managedEnd"
SHAPE_START = PREFIX + ".shapeStart"
SHAPE_END = PREFIX + ".shapeEnd"
SIG_START = PREFIX + ".sigStart"
SIG_END = PREFIX + ".sigEnd"

BUTT = 0
ROUND = 1
SQUARE = 2


def _user_data(path):
    try:
        return path.userData
    except Exception:
        return None


def is_cap_path(path):
    ud = _user_data(path)
    if not ud:
        return False
    try:
        return bool(ud.get(CAP_MARK))
    except Exception:
        return False


def _get_flag(path, key):
    ud = _user_data(path)
    if not ud:
        return False
    try:
        return bool(ud.get(key))
    except Exception:
        return False


def _set_flag(path, key, value):
    """只在值真的改變時寫入，避免開啟檔案時產生 undo 記錄。"""
    ud = _user_data(path)
    if ud is None:
        return
    value = bool(value)
    try:
        if bool(ud.get(key)) == value:
            return
    except Exception:
        pass
    ud[key] = value


def _get_float(path, key):
    ud = _user_data(path)
    if not ud:
        return None
    raw = ud.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _set_float(path, key, value, force=False):
    """只在值真的改變時寫入；force=True 時即使值是 0 也補上缺少的鍵。"""
    ud = _user_data(path)
    if ud is None:
        return
    value = float(value)
    raw = ud.get(key)
    if raw is not None:
        try:
            if abs(float(raw) - value) < 1e-9:
                return
        except (TypeError, ValueError):
            pass
    elif value == 0 and not force:
        return
    ud[key] = value


def _get_string(path, key):
    ud = _user_data(path)
    if not ud:
        return None
    raw = ud.get(key)
    return None if raw is None else str(raw)


def _set_string(path, key, value):
    """只在值真的改變時寫入；缺少鍵且值是空字串時也不寫。"""
    ud = _user_data(path)
    if ud is None:
        return
    value = str(value)
    raw = ud.get(key)
    if raw is not None:
        if str(raw) == value:
            return
    elif value == "":
        return
    ud[key] = value


def _side_keys(side):
    if side == "start":
        return MANAGED_START, SHAPE_START, SIG_START
    return MANAGED_END, SHAPE_END, SIG_END


def ensure_owner(path):
    ud = _user_data(path)
    if ud is None:
        return None
    owner = ud.get(OWNER_KEY)
    if not owner:
        owner = uuid.uuid4().hex
        ud[OWNER_KEY] = owner
    return str(owner)


def eligibility(path):
    """回傳 (是否可處理, 原因)。"""
    if path.closed:
        return False, "closed path"
    w = path.strokeWidth()
    ht = path.strokeHeight()
    if w is None:
        return False, "no native stroke"
    if ht is None:
        ht = w
    if abs(float(w) - float(ht)) > 0.01:
        return False, "strokeWidth != strokeHeight"
    pos = path.strokePosition()
    if pos not in (None, 0):
        return False, "stroke not centered"
    attrs = path.attributes
    if attrs.get("strokeGradient") is not None:
        return False, "strokeGradient is not supported"
    return True, ""


def stroke_color(path):
    try:
        return path.attributes.get("strokeColor")
    except Exception:
        return None


def _color_signature(path):
    """把 strokeColor 轉成穩定、可比較的值。"""
    try:
        color = path.attributes.get("strokeColor")
    except Exception:
        return None
    if color is None:
        return None
    try:
        return (
            round(color.redComponent(), 6),
            round(color.greenComponent(), 6),
            round(color.blueComponent(), 6),
            round(color.alphaComponent(), 6),
        )
    except Exception:
        try:
            return str(color)
        except Exception:
            return "color"


def set_cap(path, from_start, value):
    """設定原生 lineCap；值相同時完全不寫入。

    優先使用 ObjC setter，並在必要時才退回 attributes，
    避免同一次修改被寫兩遍而產生多餘的 undo 記錄。
    """
    key = "lineCapStart" if from_start else "lineCapEnd"
    getter = getattr(path, "lineCapStart" if from_start else "lineCapEnd", None)

    def current():
        if getter is None:
            return None
        try:
            return getter()
        except Exception:
            return None

    if current() == value:
        return

    setter = getattr(path, "setLineCapStart_" if from_start else "setLineCapEnd_", None)
    if setter is not None:
        try:
            setter(value)
        except Exception:
            print("CapTension：呼叫 %s 失敗" % key)
            traceback.print_exc()

    if current() == value:
        return
    try:
        path.attributes[key] = value
    except Exception:
        print("CapTension：設定 %s 失敗" % key)
        traceback.print_exc()


def path_signature(path):
    """路徑幾何與 stroke 狀態的穩定簽名。"""
    try:
        attrs = path.attributes
        w = path.strokeWidth()
        ht = path.strokeHeight()
        return repr((
            round(float(w), 4) if w is not None else None,
            round(float(ht), 4) if ht is not None else None,
            path.strokePosition(),
            tuple(
                (round(nd.position.x, 4), round(nd.position.y, 4),
                 nd.type, bool(nd.smooth))
                for nd in path.nodes
            ),
            _color_signature(path),
            attrs.get("strokeGradient") is not None,
        ))
    except Exception:
        return "err"


def end_signature(path, side, shape_value):
    return "%s|side=%s|shape=%r" % (
        path_signature(path), side, round(float(shape_value), 6))


def make_cap_path(nodes, color, owner, side):
    cap = GSPath()
    cap.closed = True
    for x, y, typ, sm in nodes:
        nd = GSNode()
        nd.type = typ
        nd.position = (x, y)
        nd.smooth = sm
        cap.nodes.append(nd)
    cap.attributes["fill"] = True
    if color is not None:
        cap.attributes["fillColor"] = color
    cap.locked = True
    cap.userData[CAP_MARK] = owner
    cap.userData[CAP_SIDE] = side
    return cap


def remove_cap(layer, cap):
    try:
        cap.locked = False
    except Exception:
        pass
    try:
        layer.removeShape_(cap)
        return True
    except Exception:
        print("CapTension：移除筆端形狀失敗")
        traceback.print_exc()
        return False


def _cap_key(cap):
    ud = _user_data(cap)
    if not ud:
        return None
    return (ud.get(CAP_MARK), ud.get(CAP_SIDE))


def layer_has_state(layer):
    """圖層是否已有 CapTension 狀態。"""
    if layer is None:
        return False
    for path in layer.paths:
        if is_cap_path(path):
            return True
        if _get_flag(path, MANAGED_START) or _get_flag(path, MANAGED_END):
            return True
    return False


def clear_targets(layer, targets=None):
    """移除指定端點的 CapTension 狀態，還原成原生方頭。

    targets=None 代表這一層所有已接管的端點；空集合代表什麼都不做。
    """
    if layer is None:
        return 0
    if targets is not None and not targets:
        return 0

    existing = {}
    for path in list(layer.paths):
        if not is_cap_path(path):
            continue
        key = _cap_key(path)
        if key is not None:
            existing.setdefault(key, []).append(path)

    removed = 0
    originals = [(i, p) for i, p in enumerate(layer.paths)
                 if not is_cap_path(p)]
    for path_index, path in originals:
        ud = _user_data(path)
        if ud is None:
            continue
        owner = ud.get(OWNER_KEY)
        owner = str(owner) if owner is not None else None
        for side in ("start", "end"):
            from_start = side == "start"
            if (targets is not None and (path, side) not in targets
                    and (owner, side) not in targets
                    and (path_index, side) not in targets):
                continue
            mkey, skey, sigkey = _side_keys(side)
            if _get_flag(path, mkey):
                set_cap(path, from_start, SQUARE)
            _set_flag(path, mkey, False)
            _set_float(path, skey, 0)
            _set_string(path, sigkey, "")
            for cap in existing.get((owner, side), []):
                if remove_cap(layer, cap):
                    removed += 1
            existing.pop((owner, side), None)

    # 清除整個圖層時，連找不到主人的孤兒端帽也一起清掉。
    if targets is None:
        for caps in existing.values():
            for cap in caps:
                if remove_cap(layer, cap):
                    removed += 1

    return removed


def update_layer(layer, shape, enabled, targets=None, manage_new=False, force_butt=False):
    """更新這一層的筆端形狀。

    targets: None = 全部合格端點；set of (path, "start"/"end") = 只處理這些。
    manage_new: True 時，選取中的方頭端會被接管；False 時只維護已接管的端點。
    force_butt: 只給「套用到選取」用；選取中的平頭端也會被接管，
                方便處理 Copy Attributes 帶過來的平頭狀態。
    回傳 (新增數, 移除數, 保留數)。
    """
    if layer is None:
        return 0, 0, 0

    # 維護模式（manage_new=False）遇到乾淨圖層時什麼都不做，
    # 避免只是開啟檔案就被寫入 owner / userData。
    if not manage_new and not layer_has_state(layer):
        return 0, 0, 0

    existing = {}
    for path in list(layer.paths):
        if not is_cap_path(path):
            continue
        key = _cap_key(path)
        if key is None or key in existing:
            # 孤兒或重複端帽只在明確套用時清理，開啟檔案時先保留。
            if manage_new:
                remove_cap(layer, path)
            continue
        existing[key] = path

    originals = [(i, p) for i, p in enumerate(layer.paths)
                 if not is_cap_path(p)]

    # 明確套用時才建立／修正 owner；維護模式保持唯讀。
    if manage_new:
        seen = set()
        for path_index, path in originals:
            owner = ensure_owner(path)
            if owner is None:
                continue
            if owner in seen:
                owner = uuid.uuid4().hex
                path.userData[OWNER_KEY] = owner
            seen.add(owner)

    made = 0
    removed = 0
    kept = 0

    for path_index, path in originals:
        if _user_data(path) is None:
            print("CapTension：路徑沒有 userData，跳過")
            continue
        owner = path.userData.get(OWNER_KEY)
        owner = str(owner) if owner is not None else None
        ok, reason = eligibility(path)

        for side in ("start", "end"):
            from_start = side == "start"
            mkey, skey, sigkey = _side_keys(side)
            cap = existing.pop((owner, side), None)
            managed = _get_flag(path, mkey)
            current_cap = path.lineCapStart() if from_start else path.lineCapEnd()
            selected = (targets is None or (path, side) in targets
                        or (owner, side) in targets
                        or (path_index, side) in targets)

            if not enabled or not ok:
                if managed:
                    set_cap(path, from_start, SQUARE)
                    _set_flag(path, mkey, False)
                    _set_float(path, skey, 0)
                    _set_string(path, sigkey, "")
                if cap is not None:
                    if remove_cap(layer, cap):
                        removed += 1
                if enabled and not ok:
                    print("CapTension：跳過路徑（%s）" % reason)
                continue

            if not selected:
                # 沒被選取：只維護已接管的端點；使用者若把 cap 改成圓頭/方頭，
                # 就交還原生設定。
                if current_cap != BUTT:
                    if managed:
                        _set_flag(path, mkey, False)
                        _set_float(path, skey, 0)
                        _set_string(path, sigkey, "")
                    if cap is not None:
                        if remove_cap(layer, cap):
                            removed += 1
                    continue
                if not managed:
                    if cap is not None:
                        if remove_cap(layer, cap):
                            removed += 1
                    continue
                stored_shape = _get_float(path, skey)
                if stored_shape is None:
                    stored_shape = shape
                dirty = False
            else:
                # 被選取：可以接管新的方頭端，或更新已接管端點的 shape。
                if current_cap == ROUND:
                    if managed:
                        _set_flag(path, mkey, False)
                        _set_float(path, skey, 0)
                        _set_string(path, sigkey, "")
                        print("CapTension：%s交還原生圓頭" % (
                            "起點" if from_start else "終點"))
                    if cap is not None:
                        if remove_cap(layer, cap):
                            removed += 1
                    continue

                if current_cap == SQUARE:
                    if managed or manage_new:
                        if not managed:
                            print("CapTension：接管%s（方頭 → 平頭 + 筆端形狀）" % (
                                "起點" if from_start else "終點"))
                        managed = True
                        set_cap(path, from_start, BUTT)
                        if manage_new:
                            stored_shape = shape
                        else:
                            stored_shape = _get_float(path, skey)
                            if stored_shape is None:
                                stored_shape = shape
                        dirty = True
                    else:
                        if cap is not None:
                            if remove_cap(layer, cap):
                                removed += 1
                        continue
                elif current_cap == BUTT:
                    if not managed:
                        if force_butt:
                            managed = True
                            stored_shape = shape
                            dirty = True
                            print("CapTension：接管%s（平頭 + 筆端形狀）" % (
                                "起點" if from_start else "終點"))
                        else:
                            if cap is not None:
                                if remove_cap(layer, cap):
                                    removed += 1
                            continue
                    elif manage_new:
                        stored_shape = shape
                        dirty = True
                    else:
                        stored_shape = _get_float(path, skey)
                        if stored_shape is None:
                            stored_shape = shape
                        dirty = False
                else:
                    if managed:
                        _set_flag(path, mkey, False)
                        _set_float(path, skey, 0)
                        _set_string(path, sigkey, "")
                    if cap is not None:
                        if remove_cap(layer, cap):
                            removed += 1
                    continue

            if owner is None:
                owner = ensure_owner(path)
            _set_flag(path, mkey, True)
            if manage_new or _get_float(path, skey) is not None:
                _set_float(path, skey, stored_shape, force=manage_new)
            current_sig = end_signature(path, side, stored_shape)
            stored_sig = _get_string(path, sigkey)

            if dirty or cap is None or current_sig != stored_sig:
                # 舊版檔案可能沒有 signature；維護模式先不重建，
                # 避免只是開啟檔案就改動文件。使用者下次套用時會補上。
                if (not manage_new and not dirty and cap is not None
                        and stored_sig is None):
                    kept += 1
                    continue
                if cap is not None:
                    if remove_cap(layer, cap):
                        removed += 1
                pts = [(nd.position.x, nd.position.y) for nd in path.nodes]
                P, t = core.end_tangent(pts, from_start)
                if P is None:
                    print("CapTension：找不到端點切線，跳過此端")
                    _set_flag(path, mkey, False)
                    _set_float(path, skey, 0)
                    _set_string(path, sigkey, "")
                    continue
                h = float(path.strokeWidth()) / 2.0
                color = stroke_color(path)
                nodes = core.cap_shape_nodes(P, t, stored_shape, h)
                new_cap = make_cap_path(nodes, color, owner, side)
                layer.addShape_(new_cap)
                _set_string(path, sigkey, current_sig)
                made += 1
            else:
                kept += 1

    # 清掉找不到主人的筆端形狀；維護模式先保留，避免開啟檔案時改動文件。
    if manage_new:
        for cap in existing.values():
            if remove_cap(layer, cap):
                removed += 1

    return made, removed, kept


def layer_signature(layer, shape, enabled):
    """用來判斷是否需要重建；不包含插件自己建立的筆端形狀內容。"""
    if layer is None:
        return ""
    parts = [
        "layer=%r" % getattr(layer, "layerId", None),
        "shape=%r" % shape,
        "enabled=%r" % enabled,
    ]
    cap_keys = []
    for path in layer.paths:
        if is_cap_path(path):
            ud = _user_data(path) or {}
            cap_keys.append((str(ud.get(CAP_MARK)), str(ud.get(CAP_SIDE))))
    parts.append("caps=%r" % sorted(cap_keys))
    for path in layer.paths:
        if is_cap_path(path):
            continue
        try:
            parts.append("path")
            parts.append("closed=%r" % path.closed)
            parts.append("w=%r h=%r pos=%r" % (
                path.strokeWidth(), path.strokeHeight(), path.strokePosition()))
            parts.append("caps=%r,%r" % (path.lineCapStart(), path.lineCapEnd()))
            parts.append("color=%r" % (_color_signature(path),))
            parts.append("gradient=%r" % (
                path.attributes.get("strokeGradient") is not None))
            parts.append("nodes=%r" % [
                (round(nd.position.x, 4), round(nd.position.y, 4),
                 nd.type, bool(nd.smooth))
                for nd in path.nodes
            ])
            ud = path.userData or {}
            parts.append("ud=%r" % (
                ud.get(OWNER_KEY),
                ud.get(MANAGED_START), ud.get(MANAGED_END),
                ud.get(SHAPE_START), ud.get(SHAPE_END),
            ))
        except Exception:
            parts.append("err")
    return "\n".join(parts)
