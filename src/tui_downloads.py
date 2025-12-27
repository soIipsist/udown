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


class DownloadDetails(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
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


class DownloadersTable(DataTable):
    def on_mount(self):
        self.add_columns(
            "URL",
            "Downloader",
            "Status",
            "Output",
            "Progress",
        )
        self.cursor_type = "row"
        self.focus()

    def load(self, downloads):
        self.clear()
        for d in downloads:
            self.add_row(
                d.url,
                str(d.downloader),
                d.download_status,
                d.output_path or "",
                d.progress,
                key=str(d.url),  # IMPORTANT: stable key
            )

    def update_progress(self, download):
        if download.id in self.rows:
            self.update_cell(str(download.id), "Progress", download.progress)


class DownloadsTable(DataTable):

    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads
        self.row_map = {}

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
        table = self
        table.clear()
        self.row_map.clear()

        for idx, d in enumerate(self.downloads):
            table.add_row(
                d.url,
                str(d.downloader),
                d.download_status,
                d.output_path or "",
                d.progress,
                key=str(d.url),
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
                    key=str(d.url),
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

        download = self.row_map.get(row)
        if download:
            self.app.push_screen(DownloadDetails(download))
            event.stop()

    def action_search(self):
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()


class UDownApp(App):
    CSS_PATH = "app.css"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("tab", "focus_next", "Focus next"),
        ("/", "search", "Search"),
        ("escape", "clear_search", "Clear search"),
    ]

    def __init__(self, downloads=None, downloaders=None):
        super().__init__()
        self.downloads = downloads or []
        self.downloaders = downloaders or []

    def compose(self):
        yield Header()
        yield Input(placeholder="Search...", id="search", classes="hidden")
        yield Container(id="table-container")
        yield Footer()

    def on_mount(self):
        self.render_table()  # default view
        self.set_interval(0.2, self.refresh_table)

    def render_table(self, table_type="downloads"):
        """Render a specific table based on type."""
        container = self.query_one("#table-container")

        if table_type == "downloads":
            table = DownloadsTable(self.downloads)
        elif table_type == "downloaders":
            table = DownloadersTable(self.downloaders)
        else:
            return

        container.mount(table)
        self.active_table = table
        self.active_table.load()  # initial load

    def refresh_table(self):
        if hasattr(self, "active_table"):
            self.active_table.refresh_table()

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
