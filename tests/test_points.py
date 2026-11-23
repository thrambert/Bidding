import unittest

from bidding.bids.points import PointZone
from bidding.utils import MyDataException

# list of tuples containing each input value and expected result
# tuple: (input zone of points, min pts, max pts, type of min, type of max)
ZONES = [
    ("8H", 8, 8, "H", "H"),
    (">12HL", 13, 40, "HL", "HL"),
    ("<=15HLD", 0, 15, "HLD", "HLD"),
    ("12-23HL", 12, 23, "HL", "HL"),
    ("16H-19HL", 16, 19, "H", "HL"),
]


class TestPoint(unittest.TestCase):
    def test_point_zone_init(self):
        for zone, min, max, type_min, type_max in ZONES:
            point_zone = PointZone(zone)
            self.assertEqual(point_zone.min, min)
            self.assertEqual(point_zone.max, max)
            self.assertEqual(point_zone.type_min, type_min)
            self.assertEqual(point_zone.type_max, type_max)
        self.assertRaises(MyDataException, PointZone, "toto")

    def test_contains(self):
        self.assertTrue(PointZone("12H-28HL").contains(pts_H=12, pts_HL=28))
        self.assertTrue(PointZone(">=12H").contains(pts_H=12, pts_HL=0))
        self.assertFalse(PointZone(">=12H").contains(pts_H=11, pts_HL=0))
        self.assertRaises(MyDataException, PointZone(">=6HLD").contains, 8, 9)

    def test_contains_HLD(self):
        self.assertTrue(PointZone(">=6HLD").contains_HLD(pts_HLD=6))
        self.assertFalse(PointZone("6-10HLD").contains_HLD(pts_HLD=11))
        self.assertRaises(MyDataException, PointZone("6-10H").contains_HLD, 8)

    def test_raises_same_exception_class_as_app(self):
        # 1b: points.py and the app must share the same MyDataException class.
        import bidding.bids.points

        self.assertIs(bidding.bids.points.MyDataException, MyDataException)
        with self.assertRaises(MyDataException):
            PointZone("no type")


if __name__ == "__main__":
    unittest.main()
