# This file starts the app.
from PyQt6.QtWidgets import QApplication
from utils import Asset
from bids.file_loaders import load_bid_rule_file
from bids.test_bidding import test_bidding


my_app = QApplication([])


def start():
   # This function starts app and proceeds to app initializations.
   Asset.set_project_root()
   try:
      load_bid_rule_file()
   except Exception as error:
      print(f"\n--> ERROR WHILE CHECKING EXCEL FILE \n{error.__str__()}\n")
      return
   print("\nExcel file successfully converted into csv compliant with BidRule model\n")
   
   test_bidding()

   # TODO: Add a_view = instance of mainWindow
   # my_app.exec()
