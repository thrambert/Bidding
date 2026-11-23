import unittest

from bridgebots.deal_enums import Direction

from bidding.deals.deal_engines import DealMaker, Vulnerability


class TestVulnerability(unittest.TestCase):
    def test_ns_ew_vuln(self):
        # 1a: values were compared to ints, so always False.
        expected = {
            Vulnerability.NONE: (False, False),
            Vulnerability.NS: (True, False),
            Vulnerability.EW: (False, True),
            Vulnerability.ALL: (True, True),
        }
        for vuln, (ns, ew) in expected.items():
            self.assertEqual((vuln.ns_vuln(), vuln.ew_vuln()), (ns, ew), vuln)


class TestDealMaker(unittest.TestCase):
    HANDS = ["AKQ9-T92-K9-AJT4", "86-J876-T75-Q982", "JT54-AKQ-A86-K76", "732-543-QJ432-53"]

    def test_random_deal_vulnerability_not_swapped(self):
        # 0b: Deal() expects ns_vulnerable before ew_vulnerable.
        deal = DealMaker(Direction.NORTH, Vulnerability.NS).create_random()
        self.assertTrue(deal.ns_vulnerable)
        self.assertFalse(deal.ew_vulnerable)

    def test_random_deal_distributes_the_52_cards(self):
        deal = DealMaker(Direction.NORTH, Vulnerability.NONE).create_random()
        cards = [card for hand in deal.hands.values() for card in hand.cards]
        self.assertEqual(len(cards), 52)
        self.assertEqual(len(set(cards)), 52)
        self.assertTrue(all(len(hand.cards) == 13 for hand in deal.hands.values()))

    def test_deal_from_str_vulnerability_not_swapped(self):
        deal = DealMaker(Direction.NORTH, Vulnerability.EW).create_from_str(self.HANDS)
        self.assertFalse(deal.ns_vulnerable)
        self.assertTrue(deal.ew_vulnerable)


if __name__ == "__main__":
    unittest.main()
