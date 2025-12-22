import inspect
from pathlib import Path
import os
from src.tui_downloads import DownloadApp
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from src.downloader import (
    Downloader,
    default_downloaders,
)
from src.download import Download, list_downloads, DownloadStatus
from tests.test_downloader import (
    playlist_urls,
    video_urls,
    wget_urls,
    urllib_urls,
    channel_urls,
)
from utils.sqlite import delete_items, create_connection, close_connection
from src.downloader import database_path

conn = create_connection(database_path)
OUTPUT_DIR = os.getcwd()


def remove_files(
    output_dir: str = OUTPUT_DIR,
    extension: str = ".py",
    excluded_extensions: list = [".txt"],
):
    for root, _, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith(extension):
                continue

            if excluded_extensions and filename.endswith(tuple(excluded_extensions)):
                continue

            file_path = os.path.join(root, filename)
            os.remove(file_path)


class TestDownload(TestBase):
    def setUp(self) -> None:
        # delete_items(conn, "downloaders", None)
        delete_items(conn, "downloads", None)
        remove_files()

        downloads = [
            Download(
                video_urls[0],
                output_filename="red.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                video_urls[1],
                downloader_type="ytdlp_audio",
                output_filename="blue.mp4",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                playlist_urls[0],
                output_filename=None,
                output_directory=OUTPUT_DIR,
            ),
            Download(
                wget_urls[1],
                downloader_type="wget",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                urllib_urls[1],
                downloader_type="urllib",
                output_directory=OUTPUT_DIR,
            ),
            Download(
                channel_urls[0],
                downloader_type="ytdlp_channel",
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
        video_downloads = [downloads[0], downloads[1]]
        wget_downloads = [Download(wget_urls[2], downloader_type="wget")]
        urllib_downloads = [Download(urllib_urls[0], downloader_type="urllib")]
        playlist_downloads = [Download(playlist_urls[0], downloader_type="ytdlp_video")]
        downloads = video_downloads

        for download in downloads:
            self.assertTrue(isinstance(download, Download))
            download: Download
            results = download.download()

    def tearDown(self):
        close_connection(conn)
        return super().tearDown()


if __name__ == "__main__":
    test_methods = [
        # TestDownload.test_list_downloads,
        # TestDownload.test_downloads_table
        TestDownload.test_download_all
    ]
    run_test_methods(test_methods)
