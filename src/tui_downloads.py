from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer
from textual.containers import Container
from textual.reactive import reactive

from src.download import Download


class DownloadApp(App):
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads

    CSS = """
    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(DataTable(id="downloads"))
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
