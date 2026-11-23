"""
Removable.
This module creates a file dna.csv with all bidding sequences from sense file,
to examine completeness of sequences.
"""

import logging
from functools import reduce

from bidding.bids.bid_rules import BidRule
from bidding.bids.bids import PASS
from bidding.bids.files import CsvFile, SenseExcelFile
from bidding.utils import Asset

logger = logging.getLogger(__name__)


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
        "G",
    ]
    BIDSYMB = [
        "-",
        "X",
        "XX",
        "nF",
        "nG",
        "FC",
        "o",
    ]

    def __init__(self, value: str):
        self.raw = value
        self.text = f"{value: ^5}"  # center padding
        self.level = int(value[0]) if value[0].isdigit() else 0
        self.suit_symbol = value[1:] if self.level >= 1 else ""

    @property
    def order(self) -> int:
        if self.suit_symbol:
            return 10 * self.level + self.SUITSYMB.index(self.suit_symbol)
        elif self.raw == "o":
            return 999
        elif self.raw in self.BIDSYMB:
            return self.BIDSYMB.index(self.raw)
        else:
            return 998

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
        self.id = f"{str(id):>4}"

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
        if other is None:
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
    Sequences with partial historic bids are ignored.
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
                logger.warning(
                    "La séquence %s figure dans les senses %s et %s",
                    sequence.raw,
                    previous_sequence.sense_id(),
                    sequence.sense_id(),
                )
            previous_sequence = sequence
        print(f"\n--> {len(self.sequences)} séquences écrites avec {count} doublons")

    def _get_all_senses(self) -> list[Sequence]:
        sequences = []
        sense_excel_file = SenseExcelFile()
        for row in sense_excel_file.get_rows():
            bidding = self._bidding(row)
            if bidding.startswith(BidRule.PARTIAL_BID_FLAG):
                continue

            sequence = Sequence(value=bidding, id=row[0])
            sequences.append(sequence)
        return sequences

    def _bidding(self, row) -> str:
        first_pass = "- - " if row[3] else ""
        hist_bid = (row[1] + " ") if row[1] else ""
        bid = "-" if row[2] == PASS else row[2]
        return first_pass + hist_bid + bid


class DnaFile(CsvFile):
    def __init__(self):
        name = Asset.path("dna.csv")
        fields = Dna.KEYS
        super().__init__(name, fields)
