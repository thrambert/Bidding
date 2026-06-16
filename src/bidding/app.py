# This file starts the app.
from PyQt6.QtWidgets import QApplication
from utils import Asset
from bids.file_loaders import FileLoader
from bids.test_bidding import test_deals


my_app = QApplication([])


def start():
   # This function starts app and proceeds to app initializations.
   Asset.set_project_root()
   try:
      FileLoader().run()
   except Exception as error:
      print(f"\n--> ERROR WHILE CHECKING EXCEL FILES \n{error.__str__()}\n")
      return
   print("\nExcel files successfully converted into csv, and compliant with related data models.\n")
   
   test_deals()

   # TODO: Add a_view = instance of mainWindow
   # my_app.exec()
