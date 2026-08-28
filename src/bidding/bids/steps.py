# This module determines in which step to compute bid for next player.
from __future__ import annotations

from enum import Enum, auto
from bids.bids import Camp


class Step(Enum):
   PASS = auto()     # impose au joueur de passer
   OPEN = auto()     # ouverture (rank 1)
   INT_N2 = auto()   # intervention du joueur n°2 (rank 2)
   REPOUV = auto()   # réponse à ouverture du joueur n°3
   RUBEN = auto()    # séquence Rubensohl (joueur n°3 et suite)
   INT_N4 = auto()   # intervention du joueur n°4
   RI_CO_N2 = auto() # réponse à intervention à la couleur du joueur 2
   RI_BI_N2 = auto() # réponse à intervention bicolore du joueur 2
   RI_UP_N2 = auto() # réponse à intervention à saut à la couleur du joueur 2
   RI_SA_N2 = auto() # réponse à intervention par 1SA du joueur 2
   RI_X_N2 = auto()  # réponse à intervention par contre d'appel du joueur 2
   RI_BI_N4 = auto() # réponse à intervention bicolore du joueur 4
   RI_UP_N4 = auto() # réponse à intervention à saut à la couleur du joueur 4
   RI_SA_N4 = auto() # réponse à intervention par 1SA du joueur 4
   RI_X_N4 = auto()  # réponse à intervention par contre d'appel du joueur 4
   REDI_N2 = auto()  # redemande de l'intervenant (joueur 2, lap 2)
   REDI_N4 = auto()  # redemande de l'intervenant (joueur 4, lap 2)
   RI2_N2 = auto()   # 2e enchère du répondant en intervention (joueur 4, lap 2)
   REDEMO = auto()   # redemande de l'ouvreur (lap 2, rank 1)
   STAYMAN = auto()  # séquence du camp de l'ouvreur selon convention Stayman
   TEXAS = auto()    # séquence du camp de l'ouvreur selon convention Texas
   SEQSA = auto()    # séquence du camp de l'ouvreur à SA
   DRURY = auto()    # séquence en réponse à 2T Drury
   SPOUTNIK = auto() # réponse au contre Spoutnik simple
   K2TX = auto()     # réponse à 1K 2T X
   RUBEN4 = auto()   # séquence redemande ouvreur après ouv 1SA et interv du N°4
   R2REP = auto()    # 2e enchère du répondant (lap 2 rank 3)
   ROUDI = auto()    # séquence convention Roudi
   RELMIN = auto()   # séquence relais dans l'autre mineure to ask opener have you 3 cards
   SAMODER = auto()  # séquence suite à 2SA modérateur
   FORCING4 = auto() # séquence suite à 4e couleur forcing
   FORCING3 = auto() # séquence suite à 3e couleur forcing
   WAKE_N1 = auto()  # réveil du joueur n°1, l'ouvreur (lap 2 rank 1)
   WAKECI = auto()   # réveil du camp en intervention (lap 2 rank 2 ou 4)
   WAKE_N3 = auto()  # réveil du joueur n°3 (lap 2 rank 3)
   OUV_2K = auto()   # séquence du camp de l'ouvreur suite ouverture de 2K
   OUV_2T = auto()   # séquence du camp de l'ouvreur suite ouverture de 2T
   OUV_2SA = auto()  # séquence du camp de l'ouvreur suite ouverture de 2SA
   FREE = auto()     # utiliser le bid producer et non le fichier des rules

   def __eq__(self, other: Step) -> bool:
      if self and other:
         return other.name == self.name
      elif self is None and other is None:
         return True
      else:
         return False
   
   @staticmethod
   def from_name(name: str) -> Step:
      if name:
         return Step[name]
      else:
         return None


class Stair:
   """
   This class provides step in which to compute bid for next player.
   Family is coming from sense file, next_step is coming from rule file.

   Algorithm
   - If a opp_next_step or camp_next_step is given in applied rule, it is
     stored in rule_steps to be applied later,
   - Else, step depends on lap and player rank.

   Properties
   player_rank:   Rank of player who has to make a bid.
   player_camp:   Camp of the player who has to make a bid.
   rule_steps:    Dict {rank: Step} for next steps provided by Excel rules.

   Constants
   LAP_RANK_STEP  Step for lap and rank. Ex lap 1, rank 3 -> 13
   WAKE:          Steps to select after 2 consecutive passes depending on rank.
   """
   LAP_RANK_STEP = {
      11: Step.OPEN,
      12: Step.INT_N2,
      13: Step.REPOUV,
      14: Step.INT_N4,
      21: Step.REDEMO,
      22: Step.FREE,
      23: Step.R2REP,
      24: Step.FREE,
   }
   WAKE = [
      Step.WAKECI,
      Step.WAKE_N3,
      Step.WAKECI,
      Step.WAKE_N1,
      ]

   def __init__(self):
      self.rule_steps: dict[int, Step] = {rank: None for rank in range(1, 5)}
   
   def get_next(self, no_bid: bool, lap_rank: int, sleep: bool) -> str:
      """
      This function returns the step on which to filter rule file for next bid.

      no_bid:     True if no bid has been made so far.
      lap_rank:   (10*lap + rank) related to the player who has to make a bid.
      sleep:      True is previous bids were 2 consecutive pass.
      """
      player_rank = lap_rank % 10
      if no_bid:
         return Step.OPEN.name
      elif self.rule_steps[player_rank]:
         return self.rule_steps[player_rank].name
      elif sleep:
         return self.WAKE[player_rank - 1].name
      elif lap_rank >= 24:
         return Step.FREE.name
      else:
         return self.LAP_RANK_STEP[lap_rank].name

   def set_next_step(self, player_rank: int, step_name: str):
      # Prepare step of the given player for his next bidding.
      next_step = Step.from_name(step_name)
      free = next_step == Step.FREE
      partner_rank = Camp.partner_rank(player_rank)
      self.rule_steps[player_rank] = next_step
      self.rule_steps[partner_rank] = Step.FREE if free else None
