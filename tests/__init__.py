# This module tells to all test modules that sources are in src folder and its sub-folders
import sys, os

_source_path = os.path.join(os.getcwd(), "src")
sys.path.insert(0, _source_path)
