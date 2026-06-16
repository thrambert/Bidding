"""
This module determines next step in which to compute bid for next player.
This next step is either given by next_step column in Excel rules, either it
is computed from bidding history.
____________________________________________________________________________
Constants giving appropriate next steps

PASS:          String value of pass special bid.
R_OPEN:        Response to opening, depending on player n°2 bid.
INT_LAP1_NO_INT:  Steps for intervener in lap 1 when no intervention before.
INTERVENE:     Steps for interveners depending on intervention count.
WAKE:          Steps to select after 2 consecutive passes depending on rank.
____________________________________________________________________________
"""
from __future__ import annotations

from enum import Enum, auto
from bids.bids import Camp
from utils import MyDataException


class Step(Enum):
   PASS = auto()     # impose au joueur de passer
   OPEN = auto()     # ouverture (rank 1)
   INT_N2 = auto()   # intervention du joueur n°2 (rank 2)
   SEQ1SA = auto()   # séquence du camp de l'ouvreur suite ouverture de 1SA
   SEQ2SA = auto()   # séquence du camp de l'ouvreur suite ouverture de 2SA
   SEQ2T = auto()    # séquence du camp de l'ouvreur suite ouverture de 2T
   SEQ2K = auto()    # séquence du camp de l'ouvreur suite ouverture de 2K
   STAYMAN = auto()  # séquence du camp de l'ouvreur selon convention Stayman
   TEXAS = auto()    # séquence du camp de l'ouvreur selon convention Texas
   ROSA = auto()     # autre réponse à ouverture dans le silence adverse (rank 3)
   ROACA = auto()    # autre réponse à ouverture après un contre d'appel (rank 3)
   ROAIC = auto()    # autre réponse à ouverture après intervention à la couleur (rank 3)
   ROA1SA = auto()   # autre réponse à ouverture après intervention à 1SA (rank 3)
   INT_N4 = auto()   # intervention du joueur n°4 (rank 4)
   REDO = auto()     # redemande de l'ouvreur (lap 2, rank 1)
   REPINT = auto()   # réponse à intervention (lap 1 rank 4, ou lap 2 rank 2)
   REDI = auto()     # redemande de l'intervenant (lap 2 rank 2 ou 4)
   R2 = auto()       # 2e enchère du répondant (lap 2 rank 3)
   INTEND = auto()   # suite du dialogue du camp en intervention, après REDI
   WAKE_N1 = auto()  # réveil du joueur n°1, l'ouvreur (lap 2 rank 1)
   WAKECI = auto()   # réveil du camp en intervention (lap 2 rank 2 ou 4)
   WAKE_N3 = auto()  # réveil du joueur n°3 (lap 2 rank 3)
   CHELEM = auto()   # séquence des controles, backwood et chelem
   FREE = auto()     # utiliser le bid producer et non le fichier des rules

   def __eq__(self, other: Step) -> bool:
      return other.name == self.name
   
   @staticmethod
   def from_name(name: str) -> Step:
      return Step[name]


class Stair:
   """
   This class provides a function to get next step.

   Properties
   bid:        Value of last bid made, "" if no bid yet made.
   lap:        Last lap in bidding.
   rank:       Rank of last bidding player (1 for opener to 4).
   rule_steps: Dict {rank: Step} for next steps provided by Excel rules.  
   """
   R_OPEN = {
      "passe": Step.ROSA,
      "X":     Step.ROACA,
      "1SA":   Step.ROA1SA,
      "other": Step.ROAIC,
   }
   INT_LAP1_NO_INT = [
      Step.INT_N2,
      Step.INT_N4,
   ]
   INTERVENE = [
      Step.PASS,
      Step.REPINT,
      Step.REDI,
      Step.INTEND,
   ]
   WAKE = [
      Step.WAKECI,
      Step.WAKE_N3,
      Step.WAKECI,
      Step.WAKE_N1,
      ]

   def __init__(self):
      self.rule_steps: dict[int, Step] = {rank: None for rank in range(1, 5)}
   
   def _update_properties(self, lap: int, player_rank: int):
      self.lap = lap
      self.player_rank = player_rank
      self.player_camp = Camp.from_rank(player_rank)

   def get_next(self, last_raw_bid: str, lap: int,
                player_rank: int, sleep: bool, intervene_count: int) -> str:
      self._update_properties(lap, player_rank)
      if self.rule_steps[player_rank]:
         return self.rule_steps[player_rank].name
      
      if not (lap and last_raw_bid):
         return Step.OPEN.name
      elif sleep:
         return self.WAKE[self.player_rank - 1].name
      elif self.player_camp == Camp.OPEN:
         return self._next_step_for_opening_camp(last_raw_bid).name
      else:
         return self._next_step_for_interv_camp(intervene_count).name

   def set_camp_next_step(self, step_name: str):
      camp_next_step = Step.from_name(step_name) if step_name else None
      partner_rank = self.player_camp.other_rank(self.player_rank)
      self.rule_steps[partner_rank] = camp_next_step
      free = camp_next_step == Step.FREE if step_name else False
      self.rule_steps[self.player_rank] = Step.FREE if free else None

   def _next_step_for_opening_camp(self, last_raw_bid: str) -> Step:
      if self.lap == 1:
         if self.player_rank == 3:
            return self._get_value(last_raw_bid, self.R_OPEN)
         else:
            return Step.REDO
      elif self.lap == 2 and self.player_rank == 3:
         return Step.R2
      else:
         print("On dépasse la 2e enchère du répondant --> Step = FREE")
         return Step.FREE
      
   def _next_step_for_interv_camp(self, interv_count: int) -> Step:
      if self.lap == 1 and interv_count == 0:
         return self.INT_LAP1_NO_INT[self.player_rank // 4]
      else:
         # Rmk: If the 2 interveners pass in first lap, they always pass after.
         return self.INTERVENE[interv_count]

   def _get_value(self, last_raw_bid: str, step_dict: dict) -> Step:
      # Returns a step from step_dict where bid is replaced by "other" if not found in.
      search_bid = last_raw_bid if last_raw_bid in step_dict else "other"
      return step_dict[search_bid]
   