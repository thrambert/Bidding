"""
Removable.
This module creates a file dna.csv with all bidding sequences from sense file,
to examine completeness of sequences.
"""
import csv
from pydantic import computed_field
from functools import reduce
from utils import Asset, MyFileAccessException
from bids.files import CsvFile
from bids.files import SemiColon, SenseExcelFile


class DnaBid:
   """
   This class stores some information on a bid.

   Properties
   raw:           Raw value of bid.
   text:          Center padding of raw value of 5 chrs length.
   level:         Level of bid or 0 if it is a special bid
   suit_symbol:   One of values from SUITSYMB below.
   order:         Integer value used to sort bids.
   SUITSYMB:      List of sorted symbolic suits.
   BIDSYMB:       Special bids values (bids without any suit).
   """
   SUITSYMB = [
      "T",
      "K",
      "C",
      "P",
      "SA",
      "m",
      "M",
      "E",
      "F",
   ]
   BIDSYMB = [
      "-",
      "X",
      "XX",
      "FC",
      "o",
   ]
   def __init__(self, value: str):
      self.raw = value
      self.text = ('{: ^5}'.format(value))  # center padding
      self.level = int(value[0]) if value[0].isdigit() else 0
      self.suit_symbol = value[1:] if self.level >= 1 else ""
   
   @computed_field
   @property
   def order(self) -> int:
      if self.suit_symbol:
         return 10 * self.level + self.SUITSYMB.index(self.suit_symbol)
      elif self.raw == "o":
         return 999
      else:
         return self.BIDSYMB.index(self.raw)

   def __lt__(self, other) -> bool:
      return self.order < other.order


class Sequence:
   """
   This class stores a sequence of one or several bids.
   
   Class variable
   sort_by_length: Sort by count first if True.

   Properties
   raw:           Raw values of bids.
   history:       List of DnaBids contained in the sequence.
   count:         Number of bids inside the sequence.
   text:          Concatenation of dna bids texts.
   id:            Right padding of Sense id of the sequence.
   
   """
   sort_by_length = False

   def __init__(self, value: str, id: int):
      self.raw = value
      self.history = [DnaBid(v) for v in value.split()]
      self.count = len(self.history)
      bid_texts = [b.text for b in self.history]
      self.text = reduce(lambda x, y: x + y, bid_texts)
      self.id = "{:>4}".format(str(id))
   
   # def __lt__(self, other) -> bool:
   #    if self.count == other.count:
   #       for i in range(0, self.count):
   #          if self.history[i].order != other.history[i].order:
   #             return self.history[i] < other.history[i]
   #    else:
   #       return self.count < other.count

   def __lt__(self, other) -> bool:
      if Sequence.sort_by_length and self.count != other.count:
         return self.count < other.count
      
      min_length = min(self.count, other.count)
      for i in range(0, min_length):
         if self.history[i].order != other.history[i].order:
            return self.history[i] < other.history[i]
      return self.count < other.count

   def __eq__(self, other) -> bool:
      if other == None or self == None:
         return False
      if self.count != other.count:
         return False
      for i in range(0, self.count):
         if self.history[i].order != other.history[i].order:
            return False
      return True

   def model_dump(self) -> dict:
      return {
         "sense_id": self.id,
         "sequence": self.text,
      }
   
   def sense_id(self) -> int:
      return int(self.id.strip())


class Dna:
   """
   This class is used to check completeness of SEFsense.xlsx sequences.
   It provides a file dna.csv with all referenced sequences defined in
   sense.csv columns hist_bid and bid.
   File is sorted using suit order as : 
   Suit order -> T, K, C, P, SA, m, M, E, F
   Bid order  -> -, X, XX, 1A, 2A..., 7A, o
   """
   KEYS = ["sense_id", "sequence"]
   
   def __init__(self, sort_by_length: bool = False):
      Sequence.sort_by_length = sort_by_length
      self.file_name = Asset.path("dna.csv")
      self.sequences = self._get_all_senses()
      self.sequences.sort()

   def write_in_file(self):
      dna_file = DnaFile()
      dna_file.recreate()
      previous_sequence = None
      count = 0
      for sequence in self.sequences:
         dna_file.add_row(sequence.model_dump())
         if sequence == previous_sequence:
            count += 1
            print(f"La séquence {sequence.raw} figure dans les senses {previous_sequence.sense_id()} et {sequence.sense_id()}")
         previous_sequence = sequence
      print(f"\n--> {len(self.sequences)} séquences écrites avec {count} doublons")

   def _get_all_senses(self) -> list[Sequence]:
      sequences = []
      sense_excel_file = SenseExcelFile()
      for row in sense_excel_file.get_rows():
         bidding = self._bidding(row)
         sequence = Sequence(value=bidding,id=row[0])
         sequences.append(sequence)
      return sequences

   def _bidding(self, row) -> str:
      first_pass = "- - " if row[4] else ""
      hist_bid = (row[1] + " ") if row[1] else ""
      bid = "-" if row[2] == "passe" else row[2]
      return first_pass + hist_bid + bid

class DnaFile(CsvFile):
   def __init__(self):
      name = Asset.path("dna.csv")
      fields = Dna.KEYS
      super().__init__(name, fields)


