import sys
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Input
from textual import events
from textual.screen import ModalScreen, Screen
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import DataTable, Header, Footer
from src.downloader import downloader_values, download_values
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.message import Message


class DownloadDetails(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("d", "delete", "Delete"),
        ("r", "download", "Retry download"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(self, download):
        super().__init__()
        self.download = download

    def compose(self):
        yield Header(show_clock=False)
        yield DataTable(id="details")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#details", DataTable)
        table.add_columns("Field", "Value")

        for key, value in self.download.as_dict().items():
            table.add_row(
                key,
                "" if value is None else str(value),
            )

    def action_delete(self):
        def on_result(confirmed: bool):
            if confirmed:
                self.dismiss()

        self.app.push_screen(
            ConfirmDelete(self.download),
            on_result,
        )

    def action_download(self) -> None:

        download = self.download
        self.app.post_message(DownloadRequested(download))


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

    def refresh_table(self):
        pass


class DownloadRequested(Message):
    def __init__(self, download):
        self.download = download
        super().__init__()


class DownloadsTable(DataTable):

    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads
        self.row_map = {}

    def set_items(self, items):
        self.downloads = items
        self.load()

    def on_mount(self):

        self.add_columns(
            "URL",
            "Downloader",
            "Status",
            "Output",
            "Progress",
        )
        self.focus()
        self.load()
        self.set_interval(0.2, self.refresh_table)

    def load(self):
        self.clear()
        self.row_map.clear()

        for idx, d in enumerate(self.downloads):
            self.add_row(
                d.url,
                str(d.downloader),
                d.download_status,
                d.output_filename,
                d.progress,
            )
            self.row_map[idx] = d

    def refresh_table(self):
        for row_index, download in self.row_map.items():
            if download.progress:
                self.update_cell(row_index, "Progress", download.progress)

    def apply_filter(self, query: str):
        self.clear()
        self.row_map.clear()
        q = query.lower().strip()
        table_row_index = 0  # real table row index

        for d in self.downloads:
            haystack = " ".join(
                str(x).lower()
                for x in (
                    d.url,
                    d.downloader,
                    d.download_status,
                    d.output_path,
                    d.progress,
                )
                if x
            )

            if q in haystack:
                self.add_row(
                    d.url,
                    str(d.downloader),
                    d.download_status,
                    d.output_path or "",
                    d.progress,
                )
                self.row_map[table_row_index] = d
                table_row_index += 1

    def on_key(self, event: events.Key) -> None:
        if event.key != "enter" or not self.has_focus:
            return

        row = self.cursor_row
        if row is None:
            return

        download = self.row_map.get(row)
        if download:
            self.app.push_screen(DownloadDetails(download))
            event.stop()


class UDownApp(App):
    CSS_PATH = "app.css"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("tab", "focus_next", "Focus next"),
        ("/", "search", "Search"),
        ("escape", "clear_search", "Clear search"),
    ]

    def __init__(self, items=None, table_type="download", action=None, args=None):
        super().__init__()
        self.items = items
        self.table_type = table_type
        self.action = action
        self.args = args

    def compose(self):
        yield Header()
        yield Input(placeholder="Search...", id="search", classes="hidden")
        yield Container(id="table-container")
        yield Footer()

    def on_mount(self):
        self.render_table()  # default view
        self.set_interval(0.2, self.refresh_progress)

    def render_table(self):
        """Render a specific table based on type."""
        container = self.query_one("#table-container")

        if self.table_type == "download":
            table = DownloadsTable(self.items)
        elif self.table_type == "downloaders":
            table = DownloadersTable(self.items)
        else:
            return

        container.mount(table)
        self.active_table = table
        self.active_table.load()  # initial load

    def refresh_progress(self):
        if hasattr(self, "active_table"):
            self.active_table.refresh_table()

    def reload_items(self):
        self.items = self.action(**self.args)

        if hasattr(self, "active_table"):
            self.active_table.set_items(self.items)

    def action_search(self):
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()

    def action_clear_search(self):
        search = self.query_one("#search", Input)
        search.value = ""
        search.add_class("hidden")
        if self.active_table:
            self.active_table.apply_filter("")

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search" and hasattr(self, "active_table"):
            self.active_table.apply_filter(event.value)

    def on_download_requested(self, message: DownloadRequested):
        download = message.download
        results = download.download()

    def on_delete_confirmed(self, message: DeleteConfirmed):
        item = message.item

        filter_condition = (
            f"url = {item.url} AND downloader_type = {item.downloader_type}"
            if self.table_type == "download"
            else f"downloader_type = {item.downloader_type}"
        )
        item.delete(filter_condition)
        self.reload_items()
