from textual.widgets import DataTable
from textual import events


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
            # Reset filter
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
        self.notify(str(row))
