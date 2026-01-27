from textual.widgets import DataTable
from textual import events
from textual.screen import ModalScreen
from textual.widgets import Input, Button
from textual.containers import Vertical
from textual.coordinate import Coordinate

from textual.screen import ModalScreen
from textual.widgets import Input, Select, Button, Static


class EditOption(ModalScreen):

    def __init__(
        self,
        key: str,
        value: str,
        choices: list[tuple[str, str]] | None = None,
    ):
        super().__init__()
        self.key = key
        self.value = str(value)
        self.choices = choices
        self.use_select = choices is not None

    def compose(self):
        yield Static(f"Edit {self.key}")

        if self.use_select:
            yield Select(options=self.choices, value=self.value, id="editor")
        else:
            yield Input(value=self.value, id="editor")

        yield Button("Save", id="save")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            value = self.query_one("#editor").value
            from src.options import set_option

            set_option(self.key, value)

        self.dismiss()


class OptionsTable(DataTable):

    def __init__(self, options):
        super().__init__()
        self._all_options = dict(options)  # original data
        self.options = dict(options)  # currently displayed data

    def set_items(self, items):
        self._all_options = dict(items)
        self.options = dict(items)
        self.load()

    def on_mount(self):
        self.add_columns("Key", "Value")
        self.focus()
        self.load()

    def apply_filter(self, query: str):
        query = query.strip().lower()

        if not query:
            self.options = dict(self._all_options)
        else:
            self.options = {
                k: v
                for k, v in self._all_options.items()
                if query in str(k).lower() or query in str(v).lower()
            }

        self.load()

    def load(self):
        self.clear()
        for key, value in self.options.items():
            self.add_row(key, value)

    def on_key(self, event: events.Key) -> None:
        if event.key != "enter" or not self.has_focus:
            return

        row = self.cursor_row
        if row is None:
            return

        key = str(self.get_cell_at(Coordinate(row, 0)))
        value = str(self.get_cell_at(Coordinate(row, 1)))

        bool_vals = ["YTDLP_UPDATE_OPTIONS", "USE_TUI"]
        op_vals = ["DOWNLOAD_OP", "DOWNLOADER_OP"]

        if key in bool_vals:
            choices = [("1", "1"), ("0", "0")]
        elif key in op_vals:
            choices = [("AND", "AND"), ("OR", "OR")]
        else:
            choices = None

        self.app.push_screen(EditOption(key, value, choices))
