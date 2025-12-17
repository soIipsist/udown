from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Input


class DownloadApp(App):
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads

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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("/", "search", "Search"),
        ("escape", "clear_search", "Clear search"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search downloads...", id="search", classes="hidden")
        yield Container(DataTable(id="downloads"))
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(
            "URL",
            "Downloader",
            "Status",
            "Output",
            "Started",
        )
        self.load()

    def reload(self, downloads):
        self.downloads = downloads
        self.load()

    def load(self):
        table = self.query_one("#downloads", DataTable)
        table.clear()

        for d in self.downloads:
            table.add_row(
                d.url,
                str(d.downloader),
                d.download_status,
                d.output_path or "",
                d.start_date,
                key=str(d.url),
            )

    def action_search(self):
        search = self.query_one("#search", Input)
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

        q = query.lower().strip()

        for d in self.downloads:
            haystack = " ".join(
                str(x).lower()
                for x in (
                    d.url,
                    d.downloader,
                    d.download_status,
                    d.output_path,
                )
                if x
            )

            if q in haystack:
                table.add_row(
                    d.url,
                    str(d.downloader),
                    d.download_status,
                    d.output_path or "",
                    d.start_date,
                    key=str(d.url),
                )
