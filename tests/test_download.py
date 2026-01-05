import inspect
from pathlib import Path
import os
import shlex
from src.tui_downloads import UDownApp
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from src.downloader import (
    Downloader,
    default_downloaders,
)
from src.download import Download, DownloadStatus, download_action
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


downloads = [
    Download(
        video_urls[0],
        downloader_type="ytdlp_video",
        output_filename="red.mp4",
        output_directory=OUTPUT_DIR,
    ),
    Download(
        video_urls[1],
        downloader_type="ytdlp_video",
        output_filename="blue.mp4",
        output_directory=OUTPUT_DIR,
    ),
    Download(
        playlist_urls[0],
        output_filename=None,
        output_directory=OUTPUT_DIR,
    ),
    Download(
        wget_urls[2],
        downloader_type="wget",
        output_directory=OUTPUT_DIR,
    ),
    Download(
        urllib_urls[2],
        downloader_type="urllib",
        output_directory=OUTPUT_DIR,
    ),
    Download(
        channel_urls[0],
        downloader_type="ytdlp_channel",
        output_directory=OUTPUT_DIR,
    ),
]

pp = PrettyPrinter(indent=1)
video_downloads = [downloads[0], downloads[1]]
wget_downloads = [Download(wget_urls[2], downloader_type="wget")]
urllib_downloads = [
    Download(urllib_urls[0], downloader_type="urllib"),
    Download(urllib_urls[-1], downloader_type="urllib"),
]
playlist_downloads = [Download(playlist_urls[0], downloader_type="ytdlp_video")]
downloads = wget_downloads


class TestDownload(TestBase):
    def setUp(self) -> None:
        # delete_items(conn, "downloaders", None)
        delete_items(conn, "downloads", None)
        remove_files()

        Download.insert_all(downloads)
        super().setUp()

    def test_list_downloads(self):
        downloads = download_action()
        pp.pprint(downloads)

    def test_download_all(self):

        for download in downloads:
            self.assertTrue(isinstance(download, Download))
            download: Download
            results = download.download()

    def test_get_extra_args(self):
        keys = ["output_directory", "hello"]
        values = ["hi", "[1,2,3]"]
        extra_args_str = ""
        for k, v in zip(keys, values):
            extra_args_str += f"{k}={v},"

        download = Download(url=wget_urls[0], extra_args=extra_args_str)
        self.assertTrue(isinstance(download.extra_args, dict))
        print(download.extra_args)

    def check_download_parts(self, parts, download: Download):
        print(parts)
        for part in parts:
            if part.startswith(("http://", "https://")):
                self.assertEqual(download.url, part)

            elif Downloader(part).select_first():
                self.assertEqual(download.downloader_type, part)

            else:
                self.assertEqual(download.output_filename, part)

    def test_parse_download_string(self):
        download_str = "https://youtu.be/MvsAesQ-4zA?si=gDyPQcdb6sTLWipY ytdlp_audio"
        downloads = Download.parse_download_string(url=download_str)
        self.assertTrue(len(downloads) == 1)

        download = downloads[0]
        self.assertTrue(isinstance(download, Download))
        download: Download
        parts = download_str.split()
        self.check_download_parts(parts, download)

    def test_parse_download_from_file(self):
        # parse from file
        filepath = "downloads.txt"
        downloads = Download.parse_download_string(url=filepath)
        new_downloads = []

        line_count = None

        with open(filepath, "r") as file:
            lines = file.readlines()
            line_count = len(lines)

            for line in lines:
                line = line.strip()
                if not line:
                    line_count -= 1
                    continue

                parts = shlex.split(line)
                downloads = Download.parse_download_string(url=line)
                download = downloads[0]

                self.check_download_parts(parts, download)
                new_downloads.append(download)

        self.assertTrue(len(downloads) == line_count)
        self.assertTrue(downloads == new_downloads)

    def tearDown(self):
        close_connection(conn)
        return super().tearDown()


if __name__ == "__main__":
    test_methods = [
        # TestDownload.test_list_downloads,
        # TestDownload.test_download_all,
        # TestDownload.test_get_extra_args,
        TestDownload.test_parse_download_string,
        # TestDownload.test_parse_download_from_file
    ]
    run_test_methods(test_methods)
