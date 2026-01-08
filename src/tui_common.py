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


class DeleteConfirmed(Message):
    def __init__(self, item):
        self.item = item
        super().__init__()


class ConfirmDelete(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("left", "move_left", "Move Left"),
        ("right", "move_right", "Move Right"),
    ]

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.buttons = []
        self.focus_index = 0

    def compose(self):
        delete_btn = Button("Delete", variant="error", id="confirm")
        cancel_btn = Button("Cancel", id="cancel")
        self.buttons = [delete_btn, cancel_btn]

        yield Vertical(
            Static("Are you sure you want to delete this item?"),
            Horizontal(delete_btn, cancel_btn),
            id="confirm-delete",
        )

    def on_mount(self):
        # Focus the first button initially
        self.buttons[self.focus_index].focus()

    def action_move_left(self):
        self.focus_index = (self.focus_index - 1) % len(self.buttons)
        self.buttons[self.focus_index].focus()

    def action_move_right(self):
        self.focus_index = (self.focus_index + 1) % len(self.buttons)
        self.buttons[self.focus_index].focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm":
            self.app.post_message(DeleteConfirmed(self.item))
            self.dismiss(True)
        else:
            self.dismiss(False)
