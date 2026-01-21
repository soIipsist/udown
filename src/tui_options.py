from textual.widgets import DataTable, Header, Footer
from textual import events
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Footer
from textual.screen import ModalScreen
from textual.message import Message
from .tui_common import ConfirmDelete


class OptionsTable(DataTable):

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.row_map = {}

    def set_items(self, items):
        self.options = items
        self.load()

    def on_mount(self):
        self.focus()
        self.load()

    def load(self):
        self.clear()
        self.row_map.clear()
