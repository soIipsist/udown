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


class TestDownload(TestBase):
    def setUp(self) -> None:
        super().setUp()
        if output_directory and os.path.exists(output_directory):
            shutil.rmtree(output_directory)


if __name__ == "__main__":
    test_methods = []
    run_test_methods(test_methods)
