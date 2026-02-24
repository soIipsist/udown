from textual.message import Message
from textual.widgets import DataTable, Header, Footer
from textual import events
from textual.screen import ModalScreen
from textual.screen import ModalScreen
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.message import Message

delete_caption = "Are you sure you want to delete this item?"
download_caption = "Start downloading this item?"
btn_confirm_delete_caption = "Delete"
btn_confirm_download_caption = "Download"


class DeleteConfirmed(Message):
    def __init__(self, item):
        self.item = item
        super().__init__()


class DownloadConfirmed(Message):
    def __init__(self, item):
        self.item = item
        super().__init__()


class ConfirmModal(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("left", "move_left", "Move Left"),
        ("right", "move_right", "Move Right"),
    ]

    def __init__(
        self,
        item,
        modal_caption=delete_caption,
        btn_variant="error",
        btn_confirm_caption=btn_confirm_delete_caption,
        message_type=DeleteConfirmed,
    ):
        super().__init__()
        self.item = item
        self.buttons = []
        self.modal_caption = modal_caption
        self.btn_variant = btn_variant
        self.btn_confirm_caption = btn_confirm_caption
        self.message_type = message_type
        self.focus_index = 0

    def compose(self):
        btn_left = Button(
            self.btn_confirm_caption, variant=self.btn_variant, id="confirm"
        )
        btn_right = Button("Cancel", id="cancel")
        self.buttons = [btn_left, btn_right]

        yield Vertical(
            Static(self.modal_caption),
            Horizontal(btn_left, btn_right),
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
            self.app.post_message(self.message_type(self.item))
            self.dismiss(True)
        else:
            self.dismiss(False)
