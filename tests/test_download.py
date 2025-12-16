import inspect
from pathlib import Path
import os
import shlex
import shutil
from src.options import METADATA_DIR
from src.tui_downloads import DownloadApp
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
from tests.test_downloader import playlist_urls, video_urls, wget_urls, urllib_urls

OUTPUT_DIR = os.getcwd()


class TestDownload(TestBase):
    def setUp(self) -> None:
        downloads = [
            Download(
                video_urls[0],
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                video_urls[1],
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                video_urls[2],
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                playlist_urls[0],
                output_filename=None,
                output_directory=OUTPUT_DIR,
            ),
            Download(
                wget_urls[0],
                output_directory=OUTPUT_DIR,
            ),
        ]
        Download.insert_all(downloads)
        super().setUp()

    def test_list_downloads(self):
        downloads = list_downloads()
        print(downloads)

    def test_downloads_table(self):
        downloads = list_downloads()
        DownloadApp(downloads).run()

    def test_download_all(self):
        downloads = list_downloads()
        downloads = [downloads[0]]

        for download in downloads:
            self.assertTrue(isinstance(download, Download))
            download: Download
            results = download.download()

            print(results)


if __name__ == "__main__":
    test_methods = [
        # TestDownload.test_list_downloads,
        # TestDownload.test_downloads_table
        TestDownload.test_download_all
    ]
    run_test_methods(test_methods)
