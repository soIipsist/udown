import os
from downloaders.ytdlp import get_channel_info
from argparse import ArgumentParser
from pprint import PrettyPrinter
from src.download import Download
from src.downloader import Downloader, get_downloader_types
from src.options import get_option

pp = PrettyPrinter(indent=2)
downloader_types = get_downloader_types()


def download(
    channel_id: str,
    downloader: str = None,
    proxy: str = None,
    sleep_interval: str = "2",
    max_sleep_interval: str = "5",
):

    if downloader is None:
        downloader = get_option("DOWNLOADER_TYPE", "ytdlp_video")
        downloader = Downloader(downloader)

    downloader = Downloader(downloader_type=downloader).select_first()

    if not downloader:
        raise ValueError(f"Downloader of type {downloader} was not found.")

    downloader: Downloader

    results = get_channel_info(channel_id)
    video_urls = [
        f"https://www.youtube.com/watch?v={entry['id']}" for entry in results["entries"]
    ]

    downloads = [
        Download(
            url=video_url,
            downloader_type=downloader,
            output_directory=os.environ.get("DOWNLOAD_DIRECTORY"),
            proxy=proxy,
            extra_args=f"sleep_interval={sleep_interval}, max_sleep_interval={max_sleep_interval}",
        )
        for video_url in video_urls
    ]

    return downloader.start_downloads(downloads)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("channel_id", type=str)
    parser.add_argument(
        "-d",
        "--downloader",
        default=get_option("DOWNLOADER_TYPE", "ytdlp_video"),
        choices=downloader_types,
    )
    parser.add_argument("-i", "--sleep_interval", default="2")
    parser.add_argument("-m", "--max_sleep_interval", default="5")
    parser.add_argument("-p", "--proxy", default=None)
    args = parser.parse_args()
    download(
        args.channel_id,
        args.downloader,
        args.proxy,
        args.sleep_interval,
        args.max_sleep_interval,
    )
