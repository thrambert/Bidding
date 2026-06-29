"""
This module is a deal generator.
"""
from bridgebots.deal import Card, Deal, PlayerHand
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
      # Returns a deal where ranks in hands are sorted from highest card to lowest
      deck = self._get_52_cards()
      hands: dict[Direction, PlayerHand] = {}
      for direction in Direction:
         hands[direction] = self._give_player_hand(deck)
      return Deal(self.dealer, self.vuln.ew_vuln(), self.vuln.ns_vuln(), hands)

   def create_from_str(self, short_cards: list[str]) -> Deal:
      # Returns a deal where ranks in hands are sorted from highest card to lowest
      #  arg is a list of card codes, as "AKQ9876-K92-K9-A" representing cards
      #  in spades, hearts, diamonds and clubs for a hand.
      #  Even if a suit has no card, a separator "-" is used.
      hands: dict[Direction, PlayerHand] = {}
      for direction in Direction:
         direction_cards = short_cards[direction.value].split("-")
         cards = []
         for suit in Suit:
            ranks = [Rank.from_str(c) for c in direction_cards[3 - suit.value]]
            cards.extend([Card(suit, rank) for rank in ranks])
         hands[direction] = PlayerHand.from_cards(cards)
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
