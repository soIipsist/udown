from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Container
from textual.reactive import reactive


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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="downloads")
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(
            "ID",
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
                str(d.id),
                d.url,
                str(d.downloader),
                d.download_status,
                d.output_path or "",
                d.start_date,
                key=str(d.id),
            )
