import unittest

from bidding.bids.bids import Bid, Camp
from bidding.bids.hands import MetaSuit
from bidding.bids.slams import Slam
from tests.helpers import make_hand


class TestBlackwoodRedemand(unittest.TestCase):
    # 1m: successive `if` let later branches overwrite the bid of earlier ones.
    def redemand(
        self, hand_spec: str, partner_raw_bid: str, nbr_trumps: int
    ) -> tuple[str, Slam.Stage]:
        slam = Slam(Camp.OPEN, MetaSuit.SPADES, nbr_trumps, 33, Bid("1P"))
        partner_bid = Bid(partner_raw_bid)
        slam.last_normal_bid = partner_bid
        sense = slam._blackwood_redemand(make_hand(hand_spec), partner_bid)
        return sense.raw_bid, slam.stage

    def test_3_keys_with_9_trumps_stops_at_minimum(self):
        # 3 aces, no trump king + partner 0 key (5T) = 3 keys.
        self.assertEqual(self.redemand("A432-A32-A32-432", "5T", 9), ("5P", Slam.Stage.STOP))

    def test_5_keys_bids_slam(self):
        # 3 aces + trump king + partner 1 key (5K) = 5 keys, 8 trumps, no queen.
        self.assertEqual(self.redemand("AK32-A32-A32-432", "5K", 8), ("6P", Slam.Stage.STOP))

    def test_4_keys_without_queen_asks_for_queen(self):
        # 4 keys + partner 0 key (5T), 8 trumps, no queen.
        self.assertEqual(self.redemand("AK32-A32-A32-432", "5T", 8), ("5K", Slam.Stage.QUEEN_ASK))


if __name__ == "__main__":
    unittest.main()
