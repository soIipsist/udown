from textual.widgets import DataTable, Header, Footer
from textual import events
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Footer
from textual.screen import ModalScreen
from .tui_common import ConfirmDelete


class DownloaderDetails(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("d", "delete", "Delete"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(self, downloader):
        super().__init__()
        self.downloader = downloader

    def compose(self):
        yield Header(show_clock=False)
        yield DataTable(id="details")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#details", DataTable)
        table.add_columns("Field", "Value")

        for key, value in self.downloader.as_dict().items():
            table.add_row(
                key,
                "" if value is None else str(value),
            )

    def action_delete(self):
        def on_result(confirmed: bool):
            if confirmed:
                self.dismiss()

        self.app.push_screen(
            ConfirmDelete(self.downloader),
            on_result,
        )


class DownloadersTable(DataTable):
    def __init__(self, downloaders):
        super().__init__()
        self.downloaders = downloaders
        self.row_map = {}

    def set_items(self, items):
        self.downloaders = items
        self.load()

    def on_mount(self):
        self.add_columns(
            "Type",
            "Path",
            "Arguments",
        )
        self.cursor_type = "row"
        self.focus()

    def load(self):
        self.clear()
        self.row_map.clear()

        for idx, d in enumerate(self.downloaders):
            self.add_row(
                d.downloader_type,
                d.downloader_path,
                d.downloader_args,
                key=str(d.downloader_type),
            )
            self.row_map[idx] = d

    def apply_filter(self, query: str):
        self.clear()
        self.row_map.clear()
        q = query.lower().strip()
        table_row_index = 0

        for d in self.downloaders:
            haystack = " ".join(
                str(x).lower()
                for x in (
                    d.downloader_type,
                    d.downloader_path,
                    d.downloader_args,
                )
                if x
            )

            if q in haystack:
                self.add_row(
                    d.downloader_type,
                    d.downloader_path,
                    d.downloader_args,
                    key=str(d.downloader_type),
                )
                self.row_map[table_row_index] = d
                table_row_index += 1

    def on_key(self, event: events.Key) -> None:
        """Open download details modal on Enter."""
        if event.key != "enter" or not self.has_focus:
            return

        row = self.cursor_row
        if row is None:
            return

        downloader = self.row_map.get(row)
        if downloader:
            self.app.push_screen(DownloaderDetails(downloader))
            event.stop()
