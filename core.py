"""連續曲線筆端（FontLab cap shape）核心幾何。

純 Python，不依賴 Glyphs。節點格式：(x, y, type, smooth)
type 為 'line' / 'curve' / 'offcurve'。
"""

import math

TOL = 0.6


def unit(dx, dy):
    d = math.hypot(dx, dy)
    if d == 0:
        raise ValueError("zero-length vector")
    return (dx / d, dy / d)


def end_tangent(pts, from_start):
    """回傳 (端點 P, 向外單位切線 t)。

    pts 為原始中線路徑的座標序列 [(x, y), ...]。
    from_start=True 取第一個點，否則取最後一個點。
    """
    seq = list(pts) if from_start else list(reversed(pts))
    P = seq[0]
    for q in seq[1:]:
        if math.hypot(P[0] - q[0], P[1] - q[1]) > 0.01:
            return P, unit(P[0] - q[0], P[1] - q[1])
    return None, None


def near(a, b):
    return abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL


def apply_caps(src, ends, h):
    """把展開輪廓 src 中的方頭角點替換成 cap shape 曲線。

    src: [(x, y, type, smooth), ...]
    ends: [(P, t, shape), ...]，P 為中線端點，t 為向外單位切線，
          shape 為 0..100。
    回傳 (新節點列表, 找到的端點數)。
    """
    n = len(src)
    out_insert, skip, to_curve, found = {}, set(), set(), 0
    for P, t, shape in ends:
        k = h * shape / 100.0
        nv = (-t[1], t[0])
        tip = (P[0] + t[0] * h, P[1] + t[1] * h)
        c_a = (tip[0] + nv[0] * h, tip[1] + nv[1] * h)
        c_b = (tip[0] - nv[0] * h, tip[1] - nv[1] * h)
        for i in range(n):
            j = (i + 1) % n
            if src[i][2] != 'line' or src[j][2] != 'line':
                continue
            pi, pj = (src[i][0], src[i][1]), (src[j][0], src[j][1])
            if not ((near(pi, c_a) and near(pj, c_b)) or
                    (near(pi, c_b) and near(pj, c_a))):
                continue
            s = 1 if near(pi, c_a) else -1
            X = (P[0] + s * nv[0] * h, P[1] + s * nv[1] * h)
            Y = (P[0] - s * nv[0] * h, P[1] - s * nv[1] * h)
            new = [
                (X[0] + t[0] * k, X[1] + t[1] * k, 'offcurve', False),
                (tip[0] + s * nv[0] * k, tip[1] + s * nv[1] * k, 'offcurve', False),
                # 最前點固定為 curve + smooth：兩段貝茲在此相切；
                # shape=0 時手柄重合，視覺上仍是尖角，但節點結構不隨 shape 改變。
                (tip[0], tip[1], 'curve', True),
                (tip[0] - s * nv[0] * k, tip[1] - s * nv[1] * k, 'offcurve', False),
                (Y[0] + t[0] * k, Y[1] + t[1] * k, 'offcurve', False),
            ]
            out_insert[(i - 1) % n] = new
            skip.update((i, j))
            to_curve.add((j + 1) % n)
            found += 1
            break
    result = []
    for i, nd in enumerate(src):
        if i in skip:
            continue
        x, y, typ, sm = nd
        if i in to_curve:
            typ = 'curve'
        result.append((x, y, typ, sm))
        if i in out_insert:
            result.extend(out_insert[i])
    return result, found


def square_cap_corners(P, t, h):
    """回傳方頭展開輪廓的兩個角點 (c_a, c_b)，方便測試與診斷。"""
    nv = (-t[1], t[0])
    tip = (P[0] + t[0] * h, P[1] + t[1] * h)
    return (
        (tip[0] + nv[0] * h, tip[1] + nv[1] * h),
        (tip[0] - nv[0] * h, tip[1] - nv[1] * h),
    )


# 端帽向筆畫內側多出的重疊長度（控制點後退距離，以半個筆畫寬 h 為單位）。
# 母版插值時，端帽底邊的旋轉是線性的，而筆畫端面會依插值後的中線重新計算，
# 兩者不一定完全重合；這段藏在筆畫裡的重疊可以避免端帽根部與筆畫分離。
REAR_OVERLAP = 1.25


def cap_shape_nodes(P, t, shape, h, rear_limit=None):
    """回傳一個「獨立筆端形狀」的封閉輪廓節點。

    這個形狀的底邊是通過 P、垂直於 t 的橫截面，範圍是 X 到 Y；
    它可以直接接在一個平頭（butt）筆畫的端點 P 上，形成新的筆端。
    底邊後方另外有一個向筆畫內側鼓起的隱藏重疊區，用來吸收母版插值時
    端帽與筆畫端面的微小角度差，避免根部出現尖縫。

    rear_limit 可限制重疊區的控制點後退距離，避免很短的筆畫被重疊區穿透。

    節點順序：X(curve) → 兩個 offcurve → tip(curve, smooth)
              → 兩個 offcurve → Y(curve) → 兩個 offcurve → 回到 X。
    重疊區的控制點深度固定為 REAR_OVERLAP * h（曲線實際鼓起約 0.75 倍），
    節點結構不隨 shape 改變。
    """
    k = h * shape / 100.0
    nv = (-t[1], t[0])
    tip = (P[0] + t[0] * h, P[1] + t[1] * h)
    # 與 apply_caps 的右端慣例一致：X 在 -nv 側、Y 在 +nv 側。
    X = (P[0] - nv[0] * h, P[1] - nv[1] * h)
    Y = (P[0] + nv[0] * h, P[1] + nv[1] * h)
    rear = h * REAR_OVERLAP
    if rear_limit is not None:
        rear = max(0.0, min(rear, float(rear_limit)))
    return [
        (X[0], X[1], 'curve', False),
        (X[0] + t[0] * k, X[1] + t[1] * k, 'offcurve', False),
        (tip[0] - nv[0] * k, tip[1] - nv[1] * k, 'offcurve', False),
        (tip[0], tip[1], 'curve', True),
        (tip[0] + nv[0] * k, tip[1] + nv[1] * k, 'offcurve', False),
        (Y[0] + t[0] * k, Y[1] + t[1] * k, 'offcurve', False),
        (Y[0], Y[1], 'curve', False),
        (Y[0] - t[0] * rear, Y[1] - t[1] * rear, 'offcurve', False),
        (X[0] - t[0] * rear, X[1] - t[1] * rear, 'offcurve', False),
    ]
