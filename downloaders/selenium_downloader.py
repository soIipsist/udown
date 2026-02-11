import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from utils.logger import setup_logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")


def get_selenium_options(options_path: str):
    if os.path.exists(options_path):
        logger.info(f"Using selenium options from path: {options_path}.")
        options = read_json_file(options_path)
    else:
        options = {}

    return options


def download(
    urls: list | str, options_path="", output_directory: str = None
) -> list[dict]:
    options = get_selenium_options(options_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selenium downloader")
    parser.add_argument("urls", nargs="+", type=str, help="URLs to scrape")
    parser.add_argument("-o", "--optons_path", default=None, type=str)
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )
    args = parser.parse_args()

    results = download(args.urls, args.output_directory)
    pp.pprint(results)
