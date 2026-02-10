import inspect
from pathlib import Path
import os
import shlex
import shutil
from src.options import DOWNLOADER_METADATA_DIR
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


video_options_1 = os.path.join(DOWNLOADER_METADATA_DIR, "video_mp4_best.json")
video_options_2 = os.path.join(DOWNLOADER_METADATA_DIR, "video_mp4_subs.json")
video_options_3 = os.path.join(DOWNLOADER_METADATA_DIR, "video_avc1.json")
wget_options = os.path.join(DOWNLOADER_METADATA_DIR, "wget_options.json")

pp = PrettyPrinter(indent=2)

# global vars
downloader_path = video_options_1
# downloads_path = "downloads.txt"
downloader_type = "ytdlp_audio"
module = "ytdlp"
downloader_func = "download"
downloader_args = "url, downloader_path"
output_directory = os.path.join(os.getcwd(), "videos")
# output_directory = None
# output_filename = "yolo.jpg"
output_filename = None


class TestDownloader(TestBase):
    def setUp(self) -> None:
        super().setUp()
        if output_directory and os.path.exists(output_directory):
            shutil.rmtree(output_directory)

    def test_get_downloader_func(self):
        downloader = Downloader("ytdlp_video", video_options_1, "ytdlp", "download")
        func = downloader.get_function()
        self.assertTrue(ytdlp_download == func)
        print(func, ytdlp_download)

    def test_get_downloader_args(self):
        downloader_args = "url, output_directory=red, ytdlp_format=ytdl"
        extra_args = "prefix=monkey, moo"
        # downloader_args = None
        func = ytdlp_download
        downloader_type = "auto"

        downloader = Downloader(
            downloader_type, downloader_path, module, func, downloader_args
        )

        download = Download(
            url=playlist_urls[0], downloader_type=downloader, extra_args=extra_args
        )

        output_downloader_args = downloader.get_downloader_args(download, func)
        func_params = inspect.signature(func).parameters
        downloader_args = downloader_args.split(",") if downloader_args else []
        # print(downloader_args)

        for arg in downloader_args:
            arg = arg.strip()
            if "=" in arg:
                k, v = arg.split("=")
                self.assertTrue(k in func_params)
                value = getattr(download, v, v)
                print(value)
            else:
                # positional arg
                value = getattr(download, arg, arg)
                print(value)

        print(output_downloader_args)

    def test_get_downloader_with_extra_args(self):
        downloader_args = "url, output_directory=red, ytdlp_format=ytdl"
        downloader = Downloader(
            downloader_type, downloader_path, module, downloader_func, downloader_args
        )
        download = Download(
            url=playlist_urls[0],
            downloader_type=downloader,
            extra_args="some_arg='hell', some_arg2='hh'",
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
        # TestDownloader.test_get_downloader_func,
        TestDownloader.test_get_downloader_args,
        # TestDownloader.test_get_downloader_with_extra_args,
        # TestDownloader.test_start_downloads,
        # TestDownloader.test_from_dict,
    ]
    run_test_methods(test_methods)
