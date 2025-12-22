from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Input
from textual import events
from textual.screen import ModalScreen
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


class DownloadApp(App):
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads
        self.conn = getattr(self.downloads[0], "conn") if len(downloads) > 0 else None
        self.row_map = {}

    CSS = """
    Screen {
        background: #0f0f14;
    }

    Header {
        background: #16161d;
        color: #cdd6f4;
    }

    Footer {
        background: #16161d;
        color: #a6adc8;
    }

    Container {
        padding: 1;
    }

    DataTable {
        background: transparent;
        color: #cdd6f4;
        border: round #313244;
    }

    DataTable > .datatable--header {
        background: #181825;
        color: #bac2de;
        text-style: bold;
    }

    DataTable > .datatable--odd-row {
        background: #0f0f14;
    }

    DataTable > .datatable--even-row {
        background: #11111b;
    }

    DataTable > .datatable--cursor {
        background: #7c3aed;      /* PURPLE */
        color: #ffffff;
        text-style: bold;
    }

    DataTable > .datatable--hover {
        background: #5b21b6;
        color: #ffffff;
    }
    
    Input#search {
        dock: top;
        margin: 1 2;
        background: #181825;
        color: #cdd6f4;
        border: round #7c3aed;
    }

    .hidden {
        display: none;
    }
    
    DownloadDetails {
        background: #0f0f14;
    }

    DownloadDetails DataTable {
        margin: 2;
        border: round #7c3aed;
        background: #11111b;
    }

    DownloadDetails > Header,
    DownloadDetails > Footer {
        background: #16161d;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("/", "search", "Search"),
        ("escape", "clear_search", "Clear search"),
        ("tab", "focus_next", "Focus next"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search downloads...", id="search", classes="hidden")
        yield DataTable(id="downloads")
        yield Footer()

    def refresh_table(self):
        table = self.query_one(DataTable)

        for row_key, download in self.download_map.items():
            if download.progress:
                table.update_cell(row_key, "Progress", download.progress)

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(
            "URL",
            "Downloader",
            "Status",
            "Output",
            "Progress",
        )
        table.focus()
        self.load()
        self.set_interval(0.2, self.refresh_table)

    def reload(self, downloads):
        self.downloads = downloads
        self.load()

    def load(self):
        table = self.query_one("#downloads", DataTable)
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

    def action_search(self):
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()

    def action_focus_next(self):
        search = self.query_one("#search", Input)
        table = self.query_one("#downloads", DataTable)

        if search.has_focus:
            search.add_class("hidden")
            table.focus()
        else:
            search.remove_class("hidden")
            search.focus()

    def action_clear_search(self):
        search = self.query_one("#search", Input)
        search.value = ""
        search.add_class("hidden")
        self.apply_filter("")

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search":
            self.apply_filter(event.value)

    def apply_filter(self, query: str):
        table = self.query_one("#downloads", DataTable)
        table.clear()
        self.row_map.clear()
        idx = 0

        q = query.lower().strip()

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
                table.add_row(
                    d.url,
                    str(d.downloader),
                    d.download_status,
                    d.output_path or "",
                    d.progress,
                    key=str(d.url),
                )
                self.row_map[idx] = d
                idx += 1

    def on_key(self, event: events.Key) -> None:
        if event.key != "enter":
            return

        table = self.query_one("#downloads", DataTable)

        if not table.has_focus:
            return

        row = table.cursor_row
        if row is None:
            return

        download = self.row_map.get(row)
        if not download:
            return

        self.push_screen(DownloadDetails(download))
        event.stop()

    def on_unmount(self) -> None:
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
