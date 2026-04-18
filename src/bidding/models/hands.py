from __future__ import annotations

from functools import cached_property, reduce
from enum import Enum
import re
from bridgebots.deal import Card, PlayerHand
from bridgebots.deal_enums import Rank, Suit
from utils import MyDataException


class SuitMeta:
   """
   This class manages suit of cards to support bidding rules, that is
   to determine which bid to make.
   """
   SUIT_FR = {
      Suit.SPADES: "pique",
      Suit.HEARTS: "coeur",
      Suit.DIAMONDS: "carreau",
      Suit.CLUBS: "trèfle",
   }
   FR_SUIT = {
      "pique": Suit.SPADES,
      "coeur": Suit.HEARTS,
      "carreau": Suit.DIAMONDS,
      "trèfle": Suit.CLUBS,
   }
   SUIT_SHORT_FR = {
      Suit.SPADES: "P",
      Suit.HEARTS: "C",
      Suit.DIAMONDS: "K",
      Suit.CLUBS: "T",
   }
   SHORT_FR_SUIT = {
      "P": Suit.SPADES,
      "C": Suit.HEARTS,
      "K": Suit.DIAMONDS,
      "T": Suit.CLUBS,
   }
   GROUP = {
      "M": "Majeure",
      "m": "mineure",
   }
   SUIT_GROUP = {
      Suit.SPADES: "M",
      Suit.HEARTS: "M",
      Suit.DIAMONDS: "m",
      Suit.CLUBS: "m",
   }

   def any_names_fr(self, suit: Suit) -> list[str]:
      # This function returns french name of suit and name of its group.
      group_abbrev= self.SUIT_GROUP[suit]
      suit_name = self.SUIT_FR[suit]
      suit_group_name = self.GROUP[group_abbrev]
      return [suit_name, suit_group_name]

   def value_validator(self, value: str) -> bool:
      """
      This function returns True if value is :
         - either a canonical suit in french (ex: coeur),
         - either a group of suits in french (ex: majeure),
         - either an abbreviation in french (ex: P, C, K, T, M, m),
      Else it raises an exception.
      """
      if value in self.GROUP.keys() + self.GROUP.values():
         return True
      if value in self.FR_SUIT.keys() + self.SHORT_FR_SUIT.keys():
         return True      
      raise MyDataException(f"La couleur {self.value} est incorrecte.")


class Distribution:
   """
   This class manages player's hand distribution to support bidding rules, that is
   to determine which bid to make.
   ____________________________________________________________________________
   Properties
   canonical : One Main enum, see below.
   numeric:    Numeric distribution or "". Example: "6322"
   special:    List of special distrib if any, or []. Example: ["bicolore 5/5"]
   ____________________________________________________________________________
   Arg for init
   value :     Either a canonical distribution in french (ex: régulier),
               either a mumeric distribution(ex: 5422),
               either a special expression (ex: bicolore 5/5).
   """
   class Main(Enum):
      REGULAR = "régulier"
      UNICOLOR = "unicolore"
      BICOLOR = "bicolore"
      TRICOLOR = "tricolore"
   

   NUM_REGULAR = [
      "4333", "4432", "5332"
      ]
   NUM_UNICOLOR = [
      "6322", "6331", "7222", "7321", "7330", "8221", "8311",
      "8320", "9211", "9220", "9310"
   ]
   NUM_BICOLOR = [
      "5422", "5431", "5521", "5530", "6421", "6430", "6511",
      "6520", "6610", "7411", "7420", "7510", "7600", "8410",
      "8500", "9400"
      ]
   NUM_TRICOLOR = [
      "4441", "5440"
      ]
   SPECIAL = {
      "bicolore 5/5": Main.BICOLOR     # Bicolor at least 5/5
   }

   def __init__(self, input_value: str):
      # Arg value is either a canonical distribution in french, either a mumeric distribution, either a special expression.
      self.canonical = self._get_canonical(input_value).value
      self.numeric: str = input_value if input_value.isdigit() else ""
      self.special: list[str] = self._get_special()

   def _get_canonical(self, input_value: str) -> Main:
      # Returns a Main enum, or None.
      if input_value in [e.value for e in self.Main]:
         return self.Main(input_value)
      elif input_value in self.NUM_REGULAR:
         return self.Main.REGULAR
      elif input_value in self.NUM_UNICOLOR:
         return self.Main.UNICOLOR
      elif input_value in self.NUM_BICOLOR:
         return self.Main.BICOLOR
      elif input_value in self.NUM_TRICOLOR:
         return self.Main.TRICOLOR
      elif input_value in self.SPECIAL.keys():
         return self.SPECIAL[input_value]
      else:
         raise MyDataException(f"La distribution {input_value} est incorrecte.")

   def _get_special(self) -> list[str]:
      # This function returns key(s) from Special dict if any.
      special_distrib = []
      if self.canonical == self.Main.BICOLOR:
         if self.numeric and int(self.numeric[:2]) >= 55:
            special_distrib.append("bicolore 5/5")
      return special_distrib
         
   def get_all_shapes(self) ->list[str]:
      # Returns all expressions for this distribution, included special if any.
      shapes = [self.canonical]
      if self.numeric:
         shapes.append(self.numeric)
      shapes.extend(self.special)
      return shapes


class RichHand:
   """
   This class described player's hand and its computed properties.
   ____________________________________________________________________________
   Public properties
   suits:         Suits dictionary. Ex: suits[SPADES] = [KING, FIVE]
   cards:         List of cards. Ex of a card: Card(suit: HEART, rank: QUEEN)
   longest_suits: The 2 suits having the most cards, see detail below.
   count_longest: Number of cards for 2 longest suits, see detail below.
   points_H:      Count of honor points
   points_HL:     Count of honor points plus distribution points
   distribution:  French distrib the hand matches with. Ex: ['régulier', '4333']
   won_tricks:    French: Levées de jeu
   def_tricks:    French: Levées sures de défense quelque soit contrat adverse
   lost_tricks:   French: Perdantes
   ____________________________________________________________________________
   Detail on longest_suits and count_longest
      They are sorted by decreasing number of cards. In cas of equality of length,
      highest suit is in first if length >= 5, else lowest suit is in first.
      Suits order from highest to lowest: spade, heart, diamond, club.
   """
   def __init__(self, player_hand: PlayerHand):
      self._player_hand = player_hand
      self.suits: dict[Suit, list[Rank]] = player_hand.suits
      self.cards: list[Card] = player_hand.cards
      self.longest_suits: tuple[Suit, Suit] = self._longest_suits_and_counts[:2]
      self.count_longest: tuple[int, int] = self._longest_suits_and_counts[2:]

   @cached_property
   def points_H(self) -> int:
      points = 0
      cards_ranks = [item for row in self.suits.values() for item in row]
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
   def points_HL(self) -> int:
      points = self.points_H
      for ranks in self.suits.values():
         points += max(0, len(ranks) - 4)
      return points

   def points_HLD(self) -> int:
      points = self.points_HL()
      # TODO: need to collect trump suit and nbr of cards in trump promised by partner
      return points
   
   @cached_property
   def distribution(self) -> list[str]:
      numeric_distrib = self._compute_numeric_distribution()
      distribution = Distribution(numeric_distrib)
      return distribution.get_all_shapes()
   
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


   def _compute_numeric_distribution(self) -> str:
      # This function returns text with numbers of cards par suit, example: 5422.
      counts = self._count_cards_per_suit.values()
      num_distrib = ""
      for n in counts:
         num_distrib += str(n)
      return num_distrib

   @cached_property
   def _longest_suits_and_counts(self) -> tuple[Suit, Suit, int, int]:
      """
      Returns 2 longest suits and their number of cards.
      If length is 5 or 6 for each, it returns highest suit first,
      if length is 4 for each, it returns lowest suit first.
      """
      suit_count = self._count_cards_per_suit
      long = list(suit_count.keys())[:2]
      count = list(suit_count.values())
      if count[0] == count[1]:
         five_or_six_cards = (count[0] >= 5)
         long.sort(key=lambda suit: suit.value, reverse=five_or_six_cards)
      return (long[0], long[1], suit_count[long[0]], suit_count[long[1]])

   @cached_property
   def _count_cards_per_suit(self) -> dict[Suit, int]:
      # This function returns nbr of cards per suit in descending order.
      count_per_suit = {key: len(value) for key, value in self.suits.items()}
      sorted_count = sorted(count_per_suit.items(), key=lambda x:x[1], reverse=True)
      return dict(sorted_count)

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
