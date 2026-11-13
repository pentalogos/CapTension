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
            (114, 430, 'line'),
            (121.5, 430, 'offcurve'),
            (129, 437.5, 'offcurve'),
            (129, 445, 'curve'),
            (129, 452.5, 'offcurve'),
            (121.5, 460, 'offcurve'),
            (114, 460, 'curve'),
        ]
        self.assertEqual(len(nodes), 7)
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
        ])

    def test_shape0_handles_coincide(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 0, 15)
        coords = [(round(x, 6), round(y, 6)) for x, y, typ, _ in nodes]
        self.assertEqual(coords, [
            (114, 430), (114, 430), (129, 445), (129, 445),
            (129, 445), (114, 460), (114, 460),
        ])

    def test_closed_contour_has_line_base(self):
        nodes = core.cap_shape_nodes((114, 445), (1, 0), 50, 15)
        self.assertEqual(nodes[0][2], 'line')
        self.assertEqual(nodes[-1][2], 'curve')


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
