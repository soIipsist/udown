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
from src.download import Download

# playlist_urls = [
#     "https://www.youtube.com/playlist?list=PL3A_1s_Z8MQbYIvki-pbcerX8zrF4U8zQ"
# ]


playlist_urls = [
    "https://www.youtube.com/playlist?list=PL4-sEuX-6HJV8C2TTbgguSByrLXKB_0WY",
    "https://www.youtube.com/playlist?list=PL4-sEuX-6HJWpbDV-SbyGUVIql65KlEhl",
]

video_urls = [
    "https://youtu.be/j17yEgxPwkk?si=mV_z1hW6oZRkvzvh",
    "https://youtu.be/tPEE9ZwTmy0?si=CvPXvCucN4ST-fcN",
]
wget_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/ChessSet.jpg/640px-ChessSet.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/e/ea/Elegant_Background-13.jpg",
    "https://ash-speed.hetzner.com/100MB.bin",
]

urllib_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/9/98/Elegant_Background-10.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/e/ea/Elegant_Background-13.jpg",
    "https://ash-speed.hetzner.com/100MB.bin",
]

channel_urls = [
    "https://www.youtube.com/playlist?list=PL4-sEuX-6HJV8C2TTbgguSByrLXKB_0WY"
]

downloader = default_downloaders[0]


video_options_1 = os.path.join(METADATA_DIR, "video_mp4_best.json")
video_options_2 = os.path.join(METADATA_DIR, "video_mp4_subs.json")
video_options_3 = os.path.join(METADATA_DIR, "video_avc1.json")
wget_options = os.path.join(METADATA_DIR, "wget_options.json")

pp = PrettyPrinter(indent=2)

# global vars
downloader_path = video_options_1
# downloads_path = "downloads.txt"
downloader_type = "ytdlp_audio"
module = "ytdlp"
func = "download"
downloader_args = "url, downloader_path, update_options=False"
output_directory = os.path.join(os.getcwd(), "videos")
# output_directory = None
# output_filename = "yolo.jpg"
output_filename = None


class TestDownloader(TestBase):
    def setUp(self) -> None:
        super().setUp()
        if output_directory and os.path.exists(output_directory):
            shutil.rmtree(output_directory)

    def test_get_extra_args(self):
        keys = ["output_directory", "hello"]
        values = ["hi", "[1,2,3]"]
        extra_args = ""
        for k, v in zip(keys, values):
            extra_args += f"{k}={v},"

        download = Download(url=wget_urls, extra_args=extra_args)
        extra_args = download.get_extra_args(extra_args)
        self.assertTrue(isinstance(extra_args, dict))
        print(extra_args)

    def test_parse_download_string(self):
        downloads_path = "downloads.txt"
        self.assertTrue(os.path.exists(downloads_path), "Missing downloads.txt file")

        with open(downloads_path, "r") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                print(line)
                download = Download.parse_download_string(line)

                self.assertIsNotNone(download, f"Failed to parse line: {line}")
                self.assertIsNotNone(download.url, f"No URL found in line: {line}")
                self.assertIn(
                    download.url,
                    line,
                    f"Parsed URL not in original line: {download.url}",
                )
                # Extract expected downloader directly from the line
                expected_downloader = "ytdlp_video"

                lexer = shlex.shlex(line, posix=False)
                lexer.whitespace_split = True
                for part in lexer:
                    if not part.startswith(("http://", "https://")) and not (
                        part.startswith('"') or part.startswith("'")
                    ):
                        expected_downloader = part
                        break

                if download.downloader:
                    self.assertTrue(
                        str(download.downloader).strip() == expected_downloader.strip(),
                        f"Expected downloader '{expected_downloader}', got '{download.downloader}' from line: {line}",
                    )

                self.assertIsNotNone(
                    download.output_directory,
                    f"Output directory should not be None for: {line}",
                )

                if download.output_filename:
                    expected_path = os.path.join(
                        download.output_directory, download.output_filename
                    )
                    self.assertEqual(
                        download.output_path,
                        expected_path,
                        f"Expected output path {expected_path}, got {download.output_path}",
                    )

    def test_get_downloader_func(self):
        downloader = Downloader("ytdlp_video", video_options_1, "ytdlp", "download")
        func = downloader.get_function()
        self.assertTrue(ytdlp_download == func)
        print(func, ytdlp_download)

    def test_get_downloader_args(self):
        downloader_args = (
            "url, output_directory=red, ytdlp_format=ytdl, update_options=url"
        )
        downloader = Downloader(
            downloader_type, downloader_path, module, func, downloader_args
        )
        download = Download(url=playlist_urls[0], downloader_type=downloader)
        output_downloader_args = downloader.get_downloader_args(
            download, ytdlp_download
        )
        func_params = inspect.signature(ytdlp_download).parameters
        downloader_args = downloader_args.split(",")

        for arg in downloader_args:
            arg = arg.strip()
            if "=" in arg:
                k, v = arg.split("=")
                self.assertTrue(k in func_params)
                print(k, output_downloader_args.get(k), v)
                value = getattr(download, v, v)
                self.assertTrue(output_downloader_args.get(k) == value)
            else:
                # positional arg
                value = getattr(download, arg, arg)

    def test_get_downloader_with_extra_args(self):
        downloader_args = (
            "url, output_directory=red, ytdlp_format=ytdl, update_options=url"
        )
        downloader = Downloader(
            downloader_type, downloader_path, module, func, downloader_args
        )
        download = Download(
            url=playlist_urls[0],
            downloader_type=downloader,
            extra_args="update_options=True, some_arg='hell', some_arg2='hh'",
        )
        output_downloader_args = downloader.get_downloader_args(
            download, ytdlp_download_channel
        )

        print(output_downloader_args)

    def test_start_downloads(self):
        downloads = [
            Download(
                playlist_urls[1],
                "ytdlp_video",
                output_directory=output_directory,
                output_filename=output_filename,
            ),
            Download(
                wget_urls[0],
                "wget",
                output_directory=output_directory,
                output_filename=output_filename,
            ),
            Download(
                urllib_urls[0],
                "urllib",
                output_directory=output_directory,
                output_filename=output_filename,
            ),
            # Download(video_urls[0], "ytdlp_audio", output_directory=output_directory),
        ]
        download_results = Downloader.start_downloads(downloads)

        print("DOWNLOAD RESULTS")
        print(len(download_results))
        playlist_counts = 0

        for result in download_results:
            if result.get("is_playlist"):
                playlist_counts += 1
                continue

        print("PLAYLIST COUNTS", playlist_counts)

    def test_from_dict(self):
        d = {"downloader_type": "ytdlp_audio"}
        downloader = Downloader.from_dict(d)
        self.assertTrue(isinstance(downloader, Downloader))

        print(downloader)


if __name__ == "__main__":
    test_methods = [
        TestDownloader.test_parse_download_string,
        # TestDownloader.test_get_downloader_func,
        # TestDownloader.test_get_downloader_args,
        # TestDownloader.test_get_downloader_with_extra_args,
        # TestDownloader.test_start_downloads,
        # TestDownloader.test_from_dict,
        # TestDownloader.test_get_extra_args
    ]
    run_test_methods(test_methods)
