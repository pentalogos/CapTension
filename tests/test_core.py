import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core  # noqa: E402


def L(x, y):
    return (x, y, 'line', False)


VEC1_SRC = [
    L(-270, 430), L(114, 430), L(129, 430), L(129, 460),
    L(114, 460), L(-270, 460), L(-285, 460), L(-285, 430),
]
VEC1_ENDS = [((114, 445), (1, 0)), ((-270, 445), (-1, 0))]

VEC1_SHAPE50 = [
    (-270, 430, 'curve', False),
    (114, 430, 'line', False),
    (121.5, 430, 'offcurve', False),
    (129, 437.5, 'offcurve', False),
    (129, 445, 'curve', False),
    (129, 452.5, 'offcurve', False),
    (121.5, 460, 'offcurve', False),
    (114, 460, 'curve', False),
    (-270, 460, 'line', False),
    (-277.5, 460, 'offcurve', False),
    (-285, 452.5, 'offcurve', False),
    (-285, 445, 'curve', False),
    (-285, 437.5, 'offcurve', False),
    (-277.5, 430, 'offcurve', False),
]


class TestVector1(unittest.TestCase):
    def run_shape(self, shape):
        ends = [(P, t, shape) for P, t in VEC1_ENDS]
        return core.apply_caps(VEC1_SRC, ends, 15.0)

    def test_shape50_exact(self):
        res, found = self.run_shape(50)
        self.assertEqual(found, 2)
        self.assertEqual(len(res), len(VEC1_SHAPE50))
        for got, want in zip(res, VEC1_SHAPE50):
            self.assertAlmostEqual(got[0], want[0], places=6)
            self.assertAlmostEqual(got[1], want[1], places=6)
            self.assertEqual(got[2], want[2])
        # 最前點固定 smooth=True，其餘節點沿用原值
        tips = [(x, y) for x, y, typ, sm in res if typ == 'curve' and sm]
        self.assertIn((129.0, 445.0), [(round(x, 6), round(y, 6)) for x, y in tips])

    def test_shape70_handles(self):
        res, found = self.run_shape(70)
        self.assertEqual(found, 2)
        # 右端：X 之後的四個手柄
        handles = [(x, y) for x, y, typ, _ in res if typ == 'offcurve' and 114 <= x <= 129.1]
        want = [(124.5, 430), (129, 434.5), (129, 455.5), (124.5, 460)]
        self.assertEqual(len(handles), 4)
        for got, exp in zip(handles, want):
            self.assertAlmostEqual(got[0], exp[0], places=6)
            self.assertAlmostEqual(got[1], exp[1], places=6)

    def test_shape100_handles_on_corners(self):
        res, found = self.run_shape(100)
        self.assertEqual(found, 2)
        handles = [(x, y) for x, y, typ, _ in res if typ == 'offcurve' and 114 <= x <= 129.1]
        want = [(129, 430), (129, 430), (129, 460), (129, 460)]
        for got, exp in zip(handles, want):
            self.assertAlmostEqual(got[0], exp[0], places=6)
            self.assertAlmostEqual(got[1], exp[1], places=6)

    def test_shape0_handles_coincide(self):
        res, found = self.run_shape(0)
        self.assertEqual(found, 2)
        self.assertEqual(len(res), len(VEC1_SHAPE50))
        # 右端 X=(114,430)、tip=(129,445)、Y=(114,460)
        for x, y, typ, _ in res:
            if typ == 'offcurve' and 114 <= x <= 129.1:
                self.assertIn((round(x, 6), round(y, 6)),
                              {(114, 430), (129, 445), (114, 460)})


VEC2_PTS = [(167, 240), (234, 187), (330, 206), (369, 80)]
VEC2_SRC = [
    (342.1, 217.6, 'offcurve', False),
    (233.2, 206.8, 'offcurve', False),
    (176.3, 251.8, 'curve', False),
    (164.5, 261.1, 'line', False),
    (145.9, 237.5, 'line', False),
    (157.7, 228.2, 'line', False),
    (234.8, 167.2, 'offcurve', False),
    (317.9, 194.4, 'offcurve', False),
    (354.7, 75.6, 'curve', False),
    (359.1, 61.2, 'line', False),
    (387.8, 70.1, 'line', False),
    (383.3, 84.4, 'line', False),
]


class TestVector2(unittest.TestCase):
    def test_tangents(self):
        P, t = core.end_tangent(VEC2_PTS, True)
        self.assertEqual(P, (167, 240))
        self.assertAlmostEqual(t[0], -0.784, places=3)
        self.assertAlmostEqual(t[1], 0.620, places=3)
        P, t = core.end_tangent(VEC2_PTS, False)
        self.assertEqual(P, (369, 80))
        self.assertAlmostEqual(t[0], 0.296, places=3)
        self.assertAlmostEqual(t[1], -0.955, places=3)

    def test_shape70_start_shape0_end(self):
        P0, t0 = core.end_tangent(VEC2_PTS, True)
        P1, t1 = core.end_tangent(VEC2_PTS, False)
        ends = [(P0, t0, 70), (P1, t1, 0)]
        res, found = core.apply_caps(VEC2_SRC, ends, 15.0)
        self.assertEqual(found, 2)
        self.assertEqual(len(res), 18)
        # 起點最前點
        start_tip = (P0[0] + t0[0] * 15, P0[1] + t0[1] * 15)
        end_tip = (P1[0] + t1[0] * 15, P1[1] + t1[1] * 15)
        self.assertAlmostEqual(start_tip[0], 155.2, places=1)
        self.assertAlmostEqual(start_tip[1], 249.3, places=1)
        self.assertAlmostEqual(end_tip[0], 373.4, places=1)
        self.assertAlmostEqual(end_tip[1], 65.7, places=1)
        # 兩個最前點確實出現在輸出中
        self.assertTrue(any(abs(x - start_tip[0]) < 0.05 and abs(y - start_tip[1]) < 0.05
                            for x, y, typ, _ in res if typ == 'curve'))
        self.assertTrue(any(abs(x - end_tip[0]) < 0.05 and abs(y - end_tip[1]) < 0.05
                            for x, y, typ, _ in res if typ == 'curve'))


class TestCapTensionNodes(unittest.TestCase):
    def test_shape50_matches_right_end(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 50, 15)
        want = [
            (114, 430, 'curve'),
            (121.5, 430, 'offcurve'),
            (129, 437.5, 'offcurve'),
            (129, 445, 'curve'),
            (129, 452.5, 'offcurve'),
            (121.5, 460, 'offcurve'),
            (114, 460, 'curve'),
            (95.25, 460, 'offcurve'),
            (95.25, 430, 'offcurve'),
        ]
        self.assertEqual(len(nodes), 9)
        for got, exp in zip(nodes, want):
            self.assertAlmostEqual(got[0], exp[0], places=6)
            self.assertAlmostEqual(got[1], exp[1], places=6)
            self.assertEqual(got[2], exp[2])

    def test_shape100_handles_on_corners(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 100, 15)
        coords = [(round(x, 6), round(y, 6)) for x, y, typ, _ in nodes]
        self.assertEqual(coords, [
            (114, 430), (129, 430), (129, 430), (129, 445),
            (129, 460), (129, 460), (114, 460),
            (95.25, 460), (95.25, 430),
        ])

    def test_shape0_handles_coincide(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 0, 15)
        coords = [(round(x, 6), round(y, 6)) for x, y, typ, _ in nodes]
        self.assertEqual(coords, [
            (114, 430), (114, 430), (129, 445), (129, 445),
            (129, 445), (114, 460), (114, 460),
            (95.25, 460), (95.25, 430),
        ])

    def test_hidden_rear_overlap(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 50, 15)
        self.assertEqual(len(nodes), 9)
        self.assertEqual(nodes[0][2], 'curve')
        self.assertEqual(nodes[-1][2], 'offcurve')
        # 後方重疊是從 Y 經兩個手柄回到 X 的曲線；中點在底邊後方 0.75*d。
        X, Y = nodes[0], nodes[6]
        rear = core.REAR_OVERLAP * 15
        mid = (
            (Y[0] + 3 * (Y[0] - rear) + 3 * (X[0] - rear) + X[0]) / 8.0,
            (Y[1] + 3 * Y[1] + 3 * X[1] + X[1]) / 8.0,
        )
        self.assertAlmostEqual(mid[0], 114 - 0.75 * rear, places=6)
        self.assertAlmostEqual(mid[1], 445, places=6)
        # 重疊區不會超出筆畫的橫向寬度。
        for x, y, typ, smooth in nodes:
            self.assertLessEqual(abs(y - 445), 15 + 1e-9)

    def test_rear_overlap_can_be_limited_for_short_segments(self):
        nodes = core.cap_shape_nodes(
            (114, 445), (1, 0), 50, 15, rear_limit=4)
        # 最後兩個手柄都只後退 4，而不是預設的 1.25 * 15。
        self.assertAlmostEqual(nodes[-1][0], 110)
        self.assertAlmostEqual(nodes[-2][0], 110)


def flatten_cap(nodes, steps=32):
    """把封閉的三次貝茲輪廓取樣成折線，供插值測試使用。"""
    start = next(i for i, nd in enumerate(nodes) if nd[2] != 'offcurve')
    ordered = nodes[start:] + nodes[:start]
    points = [(ordered[0][0], ordered[0][1])]
    current = ordered[0]
    i = 1
    while i < len(ordered):
        node = ordered[i]
        if node[2] == 'offcurve':
            controls = []
            while i < len(ordered) and ordered[i][2] == 'offcurve':
                controls.append(ordered[i])
                i += 1
            end = ordered[i] if i < len(ordered) else ordered[0]
            if i < len(ordered):
                i += 1
            if len(controls) != 2:
                raise ValueError("unexpected off-curve count")
            p0, p1, p2, p3 = current, controls[0], controls[1], end
            for step in range(1, steps + 1):
                u = step / float(steps)
                v = 1.0 - u
                points.append((
                    v ** 3 * p0[0] + 3 * v ** 2 * u * p1[0]
                    + 3 * v * u ** 2 * p2[0] + u ** 3 * p3[0],
                    v ** 3 * p0[1] + 3 * v ** 2 * u * p1[1]
                    + 3 * v * u ** 2 * p2[1] + u ** 3 * p3[1],
                ))
            current = end
        else:
            points.append((node[0], node[1]))
            current = node
            i += 1
    return points


def point_in_polygon(poly, point):
    x, y = point
    inside = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside


class TestCapInterpolation(unittest.TestCase):
    """母版插值時，端帽根部不能與筆畫端面分離。"""

    def test_hidden_rear_overlap_fills_interpolated_junction(self):
        h = 50.0
        # 兩個母版：手柄長度與端點切線方向都不同；形狀取方頭與圓頭。
        masters = [
            (150.0, 0.0),
            (40.0 * math.cos(math.radians(45)),
             40.0 * math.sin(math.radians(45))),
        ]
        shapes = (100.0, 55.23)
        caps = [
            core.cap_shape_nodes((0, 0), core.unit(*vec), shape, h)
            for vec, shape in zip(masters, shapes)
        ]
        for weight in (0.25, 0.5, 0.75):
            raw = (
                (1 - weight) * masters[0][0] + weight * masters[1][0],
                (1 - weight) * masters[0][1] + weight * masters[1][1],
            )
            face = core.unit(*raw)
            nv = (-face[1], face[0])
            nodes = [
                ((1 - weight) * x1 + weight * x2,
                 (1 - weight) * y1 + weight * y2, typ, smooth)
                for (x1, y1, typ, smooth), (x2, y2, _, _)
                in zip(caps[0], caps[1])
            ]
            poly = flatten_cap(nodes)
            # 沿著插值後的筆畫端面取樣；端面外側一點必須被端帽覆蓋。
            for i in range(-9, 10):
                lateral = h * i / 10.0
                for offset in (0.005 * h, 0.02 * h, 0.05 * h, 0.1 * h):
                    point = (
                        nv[0] * lateral + face[0] * offset,
                        nv[1] * lateral + face[1] * offset,
                    )
                    self.assertTrue(
                        point_in_polygon(poly, point),
                        "w=%r lateral=%r offset=%r" % (
                            weight, lateral, offset),
                    )


class TestHelpers(unittest.TestCase):
    def test_unit(self):
        self.assertAlmostEqual(core.unit(3, 4)[0], 0.6)
        self.assertAlmostEqual(core.unit(3, 4)[1], 0.8)

    def test_square_cap_corners_horizontal(self):
        a, b = core.square_cap_corners((114, 445), (1, 0), 15)
        self.assertAlmostEqual(a[0], 129)
        self.assertAlmostEqual(a[1], 460)
        self.assertAlmostEqual(b[0], 129)
        self.assertAlmostEqual(b[1], 430)


if __name__ == '__main__':
    unittest.main(verbosity=2)
