import os
from pathlib import Path
from downloaders.ytdlp import get_channel_info
from argparse import ArgumentParser
from pprint import PrettyPrinter
from src.downloader import get_downloader_types
from src.options import get_option
from utils.logger import setup_logger, write_output

pp = PrettyPrinter(indent=2)
downloader_types = get_downloader_types()
logger = setup_logger(name="ytdlp_extract", log_dir="/udown/ytdlp_extract")


def extract(
    url: str,
    output_directory: str = None,
    output_filename: str = None,
):
    output_directory = Path(output_directory or ".")
    output_directory.mkdir(parents=True, exist_ok=True)

    if not output_filename:
        output_filename = "downloads.txt"

    path = os.path.join(output_directory, output_filename)
    result = {"url": url, "status": 0, "path": path}

    results = get_channel_info(url)
    # logger.info(results)
    video_urls = [
        f"https://www.youtube.com/watch?v={entry['id']}" for entry in results["entries"]
    ]
    write_output(logger, video_urls, path, append=False)

    return [result]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("url", type=str)
    parser.add_argument(
        "-d", "--output_directory", type=str, default=get_option("DOWNLOAD_DIRECTORY")
    )
    parser.add_argument(
        "-f",
        "--output_filename",
        type=str,
        default=None,
        help="Output filename",
    )

    args = vars(parser.parse_args())

    urls = args.get("urls")
    output_directory = args.get("output_directory")
    output_filename = args.get("output_filename")
    results = extract(urls, output_directory, output_filename)
