"""This file starts the app."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from bidding.bids.file_loaders import FileLoader
from bidding.bids.simulations import run_simulations
from bidding.utils import Asset

logger = logging.getLogger(__name__)


def start():
    """This function starts app and proceeds to app initializations."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _qt_app = QApplication(sys.argv)
    Asset.set_project_root()
    try:
        FileLoader().run()
    except Exception as error:
        logger.error("Error while checking Excel files:\n%s", error)
        return
    logger.info("Excel files converted into csv, and compliant with related data models.")

    run_simulations()

    # TODO: Add a_view = instance of mainWindow
    # _qt_app.exec()
