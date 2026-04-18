# This module contains app utilities. It must be in same folder as main.py
#  to provide correct project_root variable.
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
   QLayout,
)


class Asset:
   # This class provides path to access assets files.
   project_root: Path = None
   _FOLDER_NAME = "assets"
   
   @staticmethod
   def path(name: str) -> Path:
      # This function returns file name of an asset in absolute path.
      return Asset.project_root.joinpath(Asset._FOLDER_NAME, name)

   @staticmethod
   def set_project_root():
   # This function loads project root path in class property whatever environment.
      if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
         # Prod: --> Project.app/Contents/Framworks
         Asset.project_root = Path(__file__).resolve().parent
      else:
         # Dev:  parents[2] of Project/src/project/main.py --> Project
         Asset.project_root = Path(__file__).resolve().parents[2]


class MyAppException(Exception):
   # This class is my base class for custom errors
   pass


class MyFileAccessException(MyAppException):
   # Manages exceptions while accessing a data file.
   def __init__(self, file_name, *args, **kwargs):
      self.msg = f"Problème lors de l'accès au fichier: {file_name}"
      super().__init__(self.msg, *args, **kwargs)


class MyUserActionException(MyAppException):
   # Manages exceptions when user did unappropriate action.
   def __init__(self, message: str):
      self.msg = message
      super().__init__(self.msg)


class MyDataException(MyAppException):
   # Manages exceptions when a data is irrelevant.
   def __init__(self, message: str):
      self.msg = message
      super().__init__(self.msg)
      

class Windower:
   """
   This class provides utils for a window.
   """
   @staticmethod
   def clear(layout: QLayout):
   # This recursive function deletes every items in layout such as
   #  sub-layouts and widgets, and also inside each sub_layout and so on.
      if layout:
         while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is None:
               Windower.clear(item.layout())
            else:
               widget.deleteLater()
