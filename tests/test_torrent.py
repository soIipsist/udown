from pathlib import Path
import os
from downloaders.torrent import *
from test_base import *
from src.options import DOWNLOADER_METADATA_DIR

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))


pp = PrettyPrinter(indent=2)
import subprocess


def check_fzf(links):

    proc = subprocess.run(
        ["fzf", "--expect=ctrl-i"],
        input="\n".join(links),
        text=True,
        capture_output=True,
    )

    lines = proc.stdout.splitlines()

    if not lines:
        return None, None

    if lines[0] == "ctrl-i":
        selection = lines[1] if len(lines) > 1 else None
        return "toggle", selection

    return "select", lines[0]


def simple_two_list_toggle():
    cmd = r"""
fzf --prompt="List A > " \
    --header="Ctrl+S = toggle" \
    --bind 'ctrl-s:reload(echo "second list item 1\nsecond list item 2")+change-prompt(List B > )' \
    --bind 'ctrl-i:reload(echo "first list item 1\nfirst list item 2")+change-prompt(List A > )'
"""
    subprocess.run(cmd, shell=True, executable="/bin/bash")


class TestTorrent(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_check_fzf(self):
        simple_two_list_toggle()

        magnet_links = []
        info_links = []

        # links = [
        #     "Ubuntu ISO|magnet:123",
        #     "Arch Linux|magnet:456",
        #     "Debian|magnet:789",
        # ]

        # action, selection = check_fzf(links)

        # print("ACTION:", action)
        # print("SELECTION:", selection)


if __name__ == "__main__":
    test_methods = [
        TestTorrent.test_check_fzf,
    ]
    run_test_methods(test_methods)
