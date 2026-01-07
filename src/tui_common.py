from textual.message import Message
from textual.widgets import DataTable, Header, Footer
from textual import events
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Footer
from textual.screen import ModalScreen
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.message import Message


class DownloadRequested(Message):
    def __init__(self, download):
        self.download = download
        super().__init__()


class DeleteConfirmed(Message):
    def __init__(self, item):
        self.item = item
        super().__init__()


class ConfirmDelete(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, item):
        super().__init__()
        self.item = item

    def compose(self):
        yield Vertical(
            Static("Are you sure you want to delete this item?"),
            Horizontal(
                Button("Delete", variant="error", id="confirm"),
                Button("Cancel", id="cancel"),
            ),
            id="confirm-delete",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm":
            self.app.post_message(DeleteConfirmed(self.item))
            self.dismiss(True)
        else:
            self.dismiss(False)
