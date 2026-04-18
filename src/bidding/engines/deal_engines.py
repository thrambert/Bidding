"""
This module is a deal generator.
"""
from bridgebots import Card, Deal, PlayerHand
from bridgebots.deal_enums import Direction, Rank, Suit
from enum import Enum
from random import randint


class Vulnerability(Enum):
   NONE = 1
   NS = 2
   EW = 3
   ALL = 4

   def ns_vuln(self) -> bool:
      return self in [2, 4]

   def ew_vuln(self) -> bool:
      return self in [3, 4]


class DealMaker:
   def __init__(self, dealer: Direction, vulnerability: Vulnerability):
      self.dealer = dealer
      self.vuln = vulnerability

   def create_random(self) -> Deal:
      deck = self._get_52_cards()
      hands: dict[Direction, PlayerHand] = {}
      for direction in Direction:
         hands[direction] = self._give_player_hand(deck)
      return Deal(self.dealer, self.vuln.ew_vuln(), self.vuln.ns_vuln(), hands)

   def create_from_str(self, short_cards: list[str]) -> Deal:
      hands: dict[Direction, PlayerHand] = {}
      for direction in Direction:
         hand_suits: dict[Suit: list[Rank]] = {}
         hand_cards = short_cards[direction.value].split("-")
         for suit in Suit:
            hand_suits[suit] = [Rank.from_str(c) for c in hand_cards[3 - suit.value]]
         hands[direction] = PlayerHand(hand_suits)
      return Deal(self.dealer, self.vuln.ew_vuln(), self.vuln.ns_vuln(), hands)
   
   def _get_52_cards(self) -> list[Card]:
      deck = []
      for suit in Suit:
         for rank in Rank:
            deck.append(Card(suit, rank))
      return deck
   
   def _give_player_hand(self, deck: list[Card]) -> PlayerHand:
      given_cards = []
      for _ in range(13):
         i = randint(0, len(deck) - 1)
         given_cards.append(deck.pop(i))
      return PlayerHand.from_cards(given_cards)
                        