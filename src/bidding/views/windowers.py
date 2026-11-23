"""This module contains Qt utilities shared by windows."""

from PyQt6.QtWidgets import QLayout


class Windower:
    """
    This class provides utils for a window.
    """

    @staticmethod
    def clear(layout: QLayout):
        """
        This recursive function deletes every items in layout such as
        sub-layouts and widgets, and also inside each sub_layout and so on.
        """
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is None:
                    Windower.clear(item.layout())
                else:
                    widget.deleteLater()
