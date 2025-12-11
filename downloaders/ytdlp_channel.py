import os
from ytdlp import get_channel_info, download
from argparse import ArgumentParser
from pprint import PrettyPrinter
from downloader import Downloader, Download, get_downloader_names

pp = PrettyPrinter(indent=2)
downloader_names = get_downloader_names()


def download(
    channel_id: str,
    downloader: str = None,
    proxy: str = None,
    sleep_interval: str = "2",
    max_sleep_interval: str = "5",
):

    if downloader is None:
        downloader = os.environ.get("DOWNLOADER_TYPE", "ytdlp_video")
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
            downloader=downloader,
            output_directory=os.environ.get("DOWNLOADS_DIRECTORY"),
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
        default=os.environ.get("DOWNLOADER_TYPE", "ytdlp_video"),
        choices=downloader_names,
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
