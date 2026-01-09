from textual import work
from textual.app import App
from textual.widgets import Header, Footer
from textual.containers import Container
from textual.widgets import Input
from textual.widgets import Header, Footer
from src.tui_downloaders import DownloadersTable
from src.tui_downloads import DownloadsTable
from src.tui_progress import ProgressScreen


class UDownApp(App):

    CSS_PATH = "app.css"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f", "filter", "Filter"),
        ("r", "refresh", "Refresh"),
        ("p", "progress", "View progress"),
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

        if self.table_type == "download":
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
            for row_index, download in self.active_table.row_map.items():
                if download.progress:
                    self.active_table.update_cell_at((row_index, 4), download.progress)

    def reload_items(self):

        self.args["ui"] = False
        self.items = self.action(**self.args)
        self.notify(str(self.args))

        if hasattr(self, "active_table"):
            self.active_table.set_items(self.items)

    def action_search(self):
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        search.focus()

    def action_clear_search(self):
        search = self.query_one("#search", Input)
        search.value = ""
        if search.visible:
            search.add_class("hidden")

    def action_refresh(self):
        self.reload_items()

    def action_filter(self):
        pass

    def action_progress(self) -> None:
        if self.table_type != "download" or not hasattr(self, "active_table"):
            self.notify(
                "Progress view is only available in the Downloads table.",
                severity="warning",
            )
            return

        self.push_screen(ProgressScreen(self.items))

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search" and hasattr(self, "active_table"):
            self.active_table.apply_filter(event.value)

    def on_download_requested(self, message):
        download = message.download
        download.download()

    def on_delete_confirmed(self, message):
        item = message.item

        filter_condition = (
            f"url = {item.url} AND downloader_type = {item.downloader_type} AND output_path = {item.output_path}"
            if self.table_type == "download"
            else f"downloader_type = {item.downloader_type}"
        )
        item.delete(filter_condition)
        self.reload_items()
