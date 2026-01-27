from textual import work
from textual.app import App
from textual.widgets import Header, Footer
from textual.containers import Container
from textual.widgets import Input
from textual.widgets import Header, Footer
from .tui_downloaders import DownloadersTable
from .tui_downloads import DownloadsTable
from .tui_options import OptionsTable
from .tui_progress import ProgressScreen


class UDownApp(App):

    CSS_PATH = "app.css"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "next_downloader_type", "Downloader →"),
        ("p", "previous_downloader_type", "Downloader ←"),
        ("r", "refresh", "Refresh"),
        # ("p", "progress", "View progress"),
        ("tab", "focus_next", "Focus next"),
        ("/", "search", "Search"),
        ("escape", "clear_search", "Clear search"),
    ]

    def __init__(
        self,
        items=None,
        table_type="download",
        action=None,
        args=None,
        downloader_types: list = None,
    ):
        super().__init__()
        self.items = items
        self.table_type = table_type
        self.action = action
        self.args = args
        self.downloader_types = downloader_types

        if self.table_type == "options":
            self.BINDINGS = [
                ("q", "quit", "Quit"),
            ]
        self.downloader_type = self.args.get("downloader_type") if self.args else None

        if self.downloader_types:
            self.downloader_types.remove("")
            if self.downloader_type in self.downloader_types:
                self.downloader_type_index = self.downloader_types.index(
                    self.downloader_type
                )
                # self.notify(f"Downloader: {self.downloader_type}", timeout=1)
            else:
                self.downloader_type_index = 0

    def compose(self):
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
        elif self.table_type == "options":
            table = OptionsTable(self.items)
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

        if self.args:
            self.args["ui"] = False

        self.items = self.action(**self.args) if self.action else self.items
        # self.notify(str(self.args))

        if hasattr(self, "active_table"):
            self.active_table.set_items(self.items)

    def set_downloader_type(self, downloader_type):
        self.args["downloader_type"] = downloader_type
        self.reload_items()

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

    def _step_downloader_type(self, step: int) -> None:
        if not self.downloader_types:
            return

        self.downloader_type_index = (self.downloader_type_index + step) % len(
            self.downloader_types
        )

        downloader_type = self.downloader_types[self.downloader_type_index]

        self.notify(f"Downloader: {downloader_type}", timeout=1)
        self.set_downloader_type(downloader_type)

    def action_previous_downloader_type(self):
        self._step_downloader_type(-1)

    def action_next_downloader_type(self):
        self._step_downloader_type(1)

    def action_progress(self) -> None:
        download = self.active_table.get_download()
        self.show_progress(download)

    def show_progress(self, download):

        if self.table_type != "download" or not hasattr(self, "active_table"):
            self.notify(
                "Progress view is only available in the Downloads table.",
                severity="warning",
            )
            return
        self.push_screen(ProgressScreen(download))

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search" and hasattr(self, "active_table"):
            self.active_table.apply_filter(event.value)

    # @work(exclusive=True)
    # async def run_download(self, download):
    #     import asyncio

    #     loop = asyncio.get_running_loop()
    #     await loop.run_in_executor(None, download.download)

    def on_download_requested(self, message):
        download = message.download
        self.notify(f"DOWNLOAD {download.downloader_type}")
        # import asyncio

        # asyncio.create_task(self.run_download(download))

    def on_delete_confirmed(self, message):
        item = message.item

        filter_condition = (
            f"url = {item.url} AND downloader_type = {item.downloader_type} AND output_path = {item.output_path}"
            if self.table_type == "download"
            else f"downloader_type = {item.downloader_type}"
        )
        item.delete(filter_condition)
        self.reload_items()
