import argparse
import re
import subprocess
import sys
from pathlib import Path
from pprint import PrettyPrinter
from utils.logger import setup_logger

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")


def download(urls: list | str, output_directory: str = None) -> list[dict]:
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selenium downloader")
    parser.add_argument("urls", nargs="+", type=str, help="URLs to scrape")
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )
    args = parser.parse_args()

    results = download(args.urls, args.output_directory)
    pp.pprint(results)
