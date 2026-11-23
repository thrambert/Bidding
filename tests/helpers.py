from bridgebots.deal import Card, PlayerHand
from bridgebots.deal_enums import Rank, Suit

from bidding.bids.bid_records import BidRecord
from bidding.bids.bid_senses import BidSense
from bidding.bids.hands import RichHand


def make_hand(spec: str) -> RichHand:
    """Builds a 13-card hand from 'spades-hearts-diamonds-clubs', e.g. 'AK32-A54-K432-32'."""
    by_suit = dict(
        zip([Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS], spec.split("-"), strict=True)
    )
    cards = [Card(suit, Rank.from_str(c)) for suit, chars in by_suit.items() for c in chars]
    return RichHand(PlayerHand.from_cards(cards))


def make_record(*raw_bids: str) -> BidRecord:
    record = BidRecord()
    for raw_bid in raw_bids:
        record.add_bidding(BidSense(id=0, raw_bid=raw_bid))
    return record
