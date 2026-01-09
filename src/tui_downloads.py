from textual.widgets import DataTable, Header, Footer
from textual import events
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Footer
from textual.screen import ModalScreen
from textual.message import Message
from src.tui_common import ConfirmDelete


class DownloadRequested(Message):
    def __init__(self, download):
        self.download = download
        super().__init__()


class DownloadDetails(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("d", "delete", "Delete"),
        ("r", "download", "Retry download"),
        ("p", "progress", "View progress"),
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
        self.dismiss()
        self.app.post_message(DownloadRequested(download))


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
                    d.downloader_type,
                    d.download_status,
                    d.output_path,
                    d.progress,
                )
                if x
            )

            if q in haystack:
                self.add_row(
                    d.url,
                    str(d.downloader_type),
                    d.download_status,
                    d.output_path or "",
                    d.progress,
                )
                self.row_map[table_row_index] = d
                table_row_index += 1

    def get_download(self):
        row = self.cursor_row
        if row is None:
            return

        download = self.row_map.get(row)
        return download

    def on_key(self, event: events.Key) -> None:
        if event.key != "enter" or not self.has_focus:
            return

        download = self.get_download()
        if download:
            self.app.push_screen(DownloadDetails(download))
            event.stop()
