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
from src.download import Download, list_downloads, DownloadStatus
from tests.test_downloader import playlist_urls, video_urls

OUTPUT_DIR = os.getcwd()


class TestDownload(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_list_downloads(self):
        downloads = [
            Download(
                video_urls[0],
                download_status=DownloadStatus.STARTED,
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                video_urls[1],
                download_status=DownloadStatus.COMPLETED,
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
        ]
        Download.insert_all(downloads)
        downloads = list_downloads()
        print(downloads)


if __name__ == "__main__":
    test_methods = [TestDownload.test_list_downloads]
    run_test_methods(test_methods)
