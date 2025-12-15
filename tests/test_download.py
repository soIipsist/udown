import inspect
from pathlib import Path
import os
import shlex
import shutil
from src.options import METADATA_DIR
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from downloaders.ytdlp import download as ytdlp_download
from downloaders.ytdlp_channel import download as ytdlp_download_channel
from src.downloader import (
    Downloader,
    default_downloaders,
)
from src.download import Download, list_downloads


class TestDownload(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_list_downloads(self):
        list_downloads()


if __name__ == "__main__":
    test_methods = [TestDownload.test_list_downloads]
    run_test_methods(test_methods)
