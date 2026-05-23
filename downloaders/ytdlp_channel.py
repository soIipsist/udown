import os
from downloaders.ytdlp import get_channel_info
from argparse import ArgumentParser
from pprint import PrettyPrinter
from src.download import Download
from src.downloader import Downloader, get_downloader_types
from src.settings import get_setting

pp = PrettyPrinter(indent=2)
downloader_types = get_downloader_types()


def download(
    channel_id: str,
    downloader_type: str = get_setting("DOWNLOADER_TYPE", "ytdlp_video"),
    proxy: str = None,
    sleep_interval: str = "2",
    max_sleep_interval: str = "5",
):

    channel_info = get_channel_info(channel_id)
    video_urls = [
        f"https://www.youtube.com/watch?v={entry['id']}" for entry in channel_info["entries"]
    ]

    downloads = [
        Download(
            url=video_url,
            downloader_type=downloader_type,
            output_directory=os.environ.get("DOWNLOAD_DIRECTORY"),
            proxy=proxy,
            extra_args={
                "sleep_interval": sleep_interval,
                "max_sleep_interval": max_sleep_interval,
            },
        )
        for video_url in video_urls
    ]

    return downloader_type.start_downloads(downloads)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("channel_id", type=str)
    parser.add_argument(
        "-d",
        "--downloader_type",
        default=get_setting("DOWNLOADER_TYPE", "ytdlp_video"),
        choices=downloader_types,
    )
    parser.add_argument("-i", "--sleep_interval", default="2")
    parser.add_argument("-m", "--max_sleep_interval", default="5")
    parser.add_argument("-p", "--proxy", default=None)
    args = parser.parse_args()
    download(
        args.channel_id,
        args.downloader_type,
        args.proxy,
        args.sleep_interval,
        args.max_sleep_interval,
    )
