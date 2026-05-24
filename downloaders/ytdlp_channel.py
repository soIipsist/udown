import os
from downloaders.ytdlp import get_channel_info, get_video_urls_from_channel
from argparse import ArgumentParser
from pprint import PrettyPrinter
from src.download import Download
from src.downloader import Downloader, get_downloader_types
from src.settings import get_setting

pp = PrettyPrinter(indent=2)
downloader_types = get_downloader_types()


def download(
    channel_id: str,
    downloader: str = get_setting("DOWNLOADER_TYPE", "ytdlp_video"),
    proxy: str = None,
    sleep_interval: str = "2",
    max_sleep_interval: str = "5",
):

    channel_url, channel_info = get_channel_info(channel_id)
    video_urls = get_video_urls_from_channel(channel_url, channel_info)

    results = []

    downloads = [
        Download(
            url=video_url,
            downloader_type=downloader,
            output_directory=os.environ.get("DOWNLOAD_DIRECTORY"),
            proxy=proxy,
            extra_args={
                "sleep_interval": sleep_interval,
                "max_sleep_interval": max_sleep_interval,
            },
        )
        for video_url in video_urls
    ]
    try:
        for download in downloads:
            result = download.download()
        results.append({"url": channel_id, "status": 0})
    except Exception as e:
        print(e)
    

    return results

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("channel_id", type=str)
    parser.add_argument(
        "-d",
        "--downloader",
        default=get_setting("DOWNLOADER_TYPE", "ytdlp_video"),
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
