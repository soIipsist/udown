from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, ProgressBar
from textual.containers import Vertical
from textual.reactive import reactive


class ProgressScreen(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
        ("p", "dismiss", "Close"),
    ]

    progress = reactive(0.0)
    eta = reactive("—")

    def __init__(self, download):
        super().__init__()
        self.download = download
        self.refresh_timer = None

    def compose(self):
        yield Header(show_clock=False)

        with Vertical(id="progress-container"):
            yield Static("", id="download-title")
            yield Static("", id="download-output")
            yield ProgressBar(total=100, id="progress-bar")
            yield Static("", id="progress-status")
            yield Static("", id="progress-eta")

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_timer = self.set_interval(0.5, self.update_progress, pause=False)
        self.update_progress()

    def on_unmount(self) -> None:
        if self.refresh_timer:
            self.refresh_timer.stop()

    def update_progress(self) -> None:
        d = self.download

        url = d.url or ""
        if len(url) > 80:
            url = url[:77] + "..."

        self.query_one("#download-title", Static).update(
            f"[bold #7c3aed]{d.downloader_type}[/] → {url}"
        )

        self.query_one("#download-output", Static).update(
            f"[dim]Output:[/] {d.output_filename or 'Determining...'}"
        )

        percent = self._parse_progress(d.progress)
        self.query_one("#progress-bar", ProgressBar).progress = percent

        self.query_one("#progress-status", Static).update(
            f"[bold green]{percent:.1f}%[/]" if percent > 0 else "[dim]Starting…[/]"
        )

        eta = getattr(d, "eta", None) or "—"
        self.query_one("#progress-eta", Static).update(f"[dim]ETA:[/] {eta}")

    def _parse_progress(self, value) -> float:
        if not value:
            return 0.0

        try:
            if isinstance(value, str) and "%" in value:
                return max(0.0, min(100.0, float(value.strip("% "))))
            return float(value)
        except Exception:
            return 0.0
