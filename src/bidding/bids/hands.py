from __future__ import annotations

from functools import cached_property, reduce
from enum import Enum
import re
from bridgebots.deal import Card, PlayerHand
from bridgebots.deal_enums import Rank, Suit
from deals.distributions import Distribution


class MetaSuit(Enum):
   """
   This class manages suits to support bidding rules, including SA.
   ____________________________________________________________________________
   Properties
   rank:       For ordering. Example: HEARTS is a lower suit than SPADES.
   suit:       item of Suit enum class or None for SA.
   text:       Name in french in lowercase, example: carreau.
   code:       A capital french letter(s) to symbolize suit, example P, SA.
   group:      two string values: mineure, Majeure, or "" for SA
   group_code: A capital letter to symbolize group: m, M, or "" for SA
   """
   CLUBS =     ("0", "trèfle", "T", "mineure")
   DIAMONDS =  ("1", "carreau", "K", "mineure")
   HEARTS =    ("2", "coeur", "C", "Majeure")
   SPADES =    ("3", "pique", "P", "Majeure")
   NO_TRUMP =  ("4", "sans atout", "SA", "")

   def __init__(self, rank_str, text, code, group):
      # args are automtically set with values defined upside ("0", "trèfle"...).
      self.rank = int(rank_str)
      self.suit = None if self.name == 'NO_TRUMP' else Suit.from_str(self.name[0])
      self.text = text
      self.code = code
      self.group = group

   @property
   def group_code(self):
      return self.group[:1] if self.group else ""
   
   def is_major(self):
      return self.group == "Majeure"
   
   def is_minor(self):
      return self.group == "mineure"

   def __lt__(self, other) -> bool:
      return self.rank < other.rank

   def __repr__(self) -> str:
      return self.text

   def any_texts(self) -> list[str]:
      return [self.text, self.group]
   
   def any_codes(self) -> list[str]:
      return [self.code, self.group_code]
   
   @staticmethod
   def real() -> list:
      return [s for s in MetaSuit if s != MetaSuit.NO_TRUMP]
   @staticmethod
   def from_suit(suit: Suit) -> MetaSuit:
      meta_suit = [s for s in MetaSuit if s.name == suit.name]
      return meta_suit[0] if meta_suit else None

   @staticmethod
   def from_text(suit_text: str) -> MetaSuit:
      meta_suit = [s for s in MetaSuit if s.text == suit_text]
      return meta_suit[0] if meta_suit else None

   @staticmethod
   def from_code(suit_code: str) -> MetaSuit:
      meta_suit = [s for s in MetaSuit if s.code == suit_code]
      return meta_suit[0] if meta_suit else None

   @staticmethod
   def all_texts() -> list[str]:
      return [s.text for s in MetaSuit]

   @staticmethod
   def all_groups() -> list[str]:
      return ["Majeure", "mineure"]


class RichHand:
   """
   This class described player's hand and its computed properties.
   ____________________________________________________________________________
   Public properties
   suits:         dict[MetaSuit, list[Rank]], ex: suits[SPADES] = [KING, FIVE]
   cards:         List of cards. Ex of a card: Card(suit: HEART, rank: QUEEN)
   longest_suits: The 2 suits having the most cards, see detail below.
   count_longest: Number of cards for 2 longest suits, see detail below.
   points_H:      Count of honor points
   points_HL:     Count of honor points plus distribution points
   distribution:  French distrib the hand matches with. Ex: ['régulier', '4333']
   cards_count:   Number of cards per suit in descending order.
   majors_count:  Number of cards per major suit.
   won_tricks:    French: Levées de jeu
   def_tricks:    French: Levées sures de défense quelque soit contrat adverse
   lost_tricks:   French: Perdantes
   best_minor_code:  Longest minor suit code, or club if eq 3, or diamond if eq 4
   best_major_code:  Longest major suit code, or heart if eq 4, or spade if eq 5
   ____________________________________________________________________________
   Detail on suits
      Ranks in suit are sorted from highest card ACE to lowest TWO.
   Detail on longest_suits and count_longest
      They are sorted by decreasing number of cards. In cas of equality of length,
      highest suit is in first if length >= 5, else lowest suit is in first.
      Suits order from highest to lowest: spade, heart, diamond, club.
   """
   def __init__(self, player_hand: PlayerHand):
      self._player_hand = player_hand
      self.suits = {MetaSuit.from_suit(k): v for k, v in player_hand.suits.items()}
      self.cards: list[Card] = player_hand.cards
      self.longest_suits: tuple[MetaSuit, MetaSuit] = self._longest_suits_and_counts[:2]
      self.count_longest: tuple[int, int] = self._longest_suits_and_counts[2:]

   @cached_property
   def points_H(self) -> int:
      points = 0
      for meta_suit in MetaSuit.real():
         points += self.suit_points_H(meta_suit)
      return points
   
   @cached_property
   def points_HL(self) -> int:
      points = self.points_H
      for ranks in self.suits.values():
         points += max(0, len(ranks) - 4)
      return points

   def points_HLD(self) -> int:
      points = self.points_HL
      # TODO: need to collect trump suit and nbr of cards in trump promised by partner
      return points
   
   def suit_points_H(self, meta_suit: MetaSuit) -> int:
      points = 0
      cards_ranks = self.suits[meta_suit]
      for rank in cards_ranks:
         match rank:
            case Rank.JACK:
               points += 1
            case Rank.QUEEN:
               points += 2
            case Rank.KING:
               points += 3
            case Rank.ACE:
               points += 4
      return points

   @cached_property
   def distribution(self) -> list[str]:
      numeric_distrib = self._compute_numeric_distribution()
      distribution = Distribution(numeric_distrib)
      return distribution.get_all_shapes()
   
   @cached_property
   def cards_count(self) -> dict[MetaSuit, int]:
      count_per_suit = {MetaSuit.from_suit(k): len(v) for k, v in self.suits.items()}
      sorted_count = sorted(count_per_suit.items(), key=lambda x:x[1], reverse=True)
      return dict(sorted_count)

   @cached_property
   def majors_count(self) -> dict[MetaSuit, int]:
      return {
         MetaSuit.SPADES: len(self.suits[MetaSuit.SPADES]),
         MetaSuit.HEARTS: len(self.suits[MetaSuit.HEARTS]),
      }

   @cached_property
   def won_tricks(self) -> float:
      tricks = 0
      for string_cards in self._string_cards.values():
         tricks += self._won_tricks_length(len(string_cards))
         tricks += self._won_tricks_honors(string_cards)
      return tricks

   @cached_property
   def def_tricks(self) -> int:
      tricks = 0
      for suit_string_cards in self._string_cards.values():
         if re.match('AR', suit_string_cards):
            tricks += 2 if len(suit_string_cards) < 6 else 1
         elif re.match('A', suit_string_cards):
            tricks += 1
      return tricks

   @cached_property
   def lost_tricks(self) -> int:
      tricks = 0
      for suit_string_cards in self._string_cards.values():
         matched = re.findall('[AKQ]', suit_string_cards)
         tricks += 3 - len(matched)
      return tricks

   @cached_property
   def best_minor_code(self) -> str:
      if self.cards_count[MetaSuit.DIAMONDS] > self.cards_count[MetaSuit.CLUBS]:
         return MetaSuit.DIAMONDS.group_code
      elif self.cards_count[MetaSuit.DIAMONDS] < self.cards_count[MetaSuit.CLUBS]:
         return MetaSuit.CLUBS.group_code
      elif self.cards_count[MetaSuit.DIAMONDS] == 3:
         return MetaSuit.CLUBS.group_code
      else:
         return MetaSuit.DIAMONDS.group_code

   @cached_property
   def best_major_code(self) -> str:
      if self.cards_count[MetaSuit.SPADES] > self.cards_count[MetaSuit.HEARTS]:
         return MetaSuit.SPADES.group_code
      elif self.cards_count[MetaSuit.SPADES] < self.cards_count[MetaSuit.HEARTS]:
         return MetaSuit.HEARTS.group_code
      elif self.cards_count[MetaSuit.SPADES] <= 4:
         return MetaSuit.HEARTS.group_code
      else:
         return MetaSuit.SPADES.group_code

   def stop_suit(self, suit: MetaSuit) -> bool:
      # Returns True if this hand has one or more stops in given suit.
      count = 0
      ranks = self.suits[suit]
      if len(ranks) == 0:
         return False
      elif ranks[0].value < 11:     # JACK.value = 11
         return False
      else:
         return len(ranks) >= 15 - ranks[0].value  # ACE.value = 14, KING = 13...
   
   def controlled_suits(self) -> list[str]:
      controls = []
      for meta_suit, ranks in self.suits.items():
         king_control = (ranks[0] == Rank.KING and len(ranks) >= 2)
         if len(ranks) <= 1 or ranks[0] == Rank.ACE or king_control:
            controls.append(meta_suit)
      return controls

   def _compute_numeric_distribution(self) -> str:
      # This function returns text with numbers of cards par suit, example: 5422.
      count_per_suit = [str(n) for n in self.cards_count.values()]
      return reduce(lambda x, y: x + y, count_per_suit)

   @cached_property
   def _longest_suits_and_counts(self) -> tuple[MetaSuit, MetaSuit, int, int]:
      """
      Returns 2 longest suits and their number of cards.
      If length is 5 or 6 for each, it returns highest suit first,
      if length is 4 for each, it returns lowest suit first.
      """
      suit_count = self.cards_count
      long = list(suit_count.keys())[:2]
      count = list(suit_count.values())
      if count[0] == count[1]:
         five_or_six_cards = (count[0] >= 5)
         long.sort(key=lambda suit: suit.value, reverse=five_or_six_cards)
      return (long[0], long[1], suit_count[long[0]], suit_count[long[1]])

   def _won_tricks_length(self, count: int) -> float:
      if count == 4:
         return 0.5
      elif count == 5:
         return 1.5
      elif count >= 6:
         return float(count) - 3
      else:
         return 0
      
   def _won_tricks_honors(self, suit_string_cards: str) -> float:
      HONORS_WON_TRICKS = {
         'AKQ': 3,
         'AKJ': 2.5,
         'AQJ': 2.25,
         'AK':  2,
         'AQ.': 1.5,
         'A':   1,
         'KQJ': 2,
         'KQ.': 1.25,
         'K.':  0.5,
         'QJ.': 0.75,
         'QT9': 0.75,
         'Q.':  0.25,
      }
      for pattern, value in HONORS_WON_TRICKS.items():
         if re.match(pattern, suit_string_cards):
            return value
         else:
            return 0

   @cached_property
   def _string_cards(self) -> dict[Suit, str]:
      # Returns cards of suits in reverse order, as "AKQ94".
      cards_per_suits = {}
      for suit, ranks in self.suits.items():
         sorted_ranks = sorted(ranks, reverse=True)
         short_cards = [r.abbreviation() for r in sorted_ranks]
         string_cards = "".join(c for c in short_cards)
         cards_per_suits[suit] = string_cards
      return cards_per_suits

   def __repr__(self):
      return self._player_hand.__repr__()
