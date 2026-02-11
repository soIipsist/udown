import argparse
import os
from pathlib import Path
from pprint import PrettyPrinter

from downloaders.ytdlp import read_json_file
from utils.logger import setup_logger

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")


def get_chrome_options(options: dict, output_directory: Path | None = None) -> Options:
    chrome_options = Options()

    # chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-gpu")

    chrome_config = options.get("chrome_options", {})

    prefs = {}
    if output_directory:
        prefs.update(
            {
                "download.default_directory": str(output_directory.resolve()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            }
        )

    for key, value in chrome_config.items():

        if key == "arguments" and isinstance(value, list):
            for arg in value:
                chrome_options.add_argument(arg)

        elif key == "prefs" and isinstance(value, dict):
            prefs.update(value)

        elif key == "experimental_options" and isinstance(value, dict):
            for exp_key, exp_val in value.items():
                chrome_options.add_experimental_option(exp_key, exp_val)

        else:
            logger.warning(f"Unknown chrome option key ignored: {key}")

    if prefs:
        chrome_options.add_experimental_option("prefs", prefs)

    return chrome_options


def get_selenium_options(options_path: str | None, output_directory: Path | None):
    if options_path and os.path.exists(options_path):
        logger.info(f"Using selenium options from path: {options_path}")
        options = read_json_file(options_path)
    else:
        options = {}

    chrome_options = get_chrome_options(options, output_directory)
    options["chrome_options"] = chrome_options
    return options


def download(
    url: str,
    options_path: str | None = None,
    output_directory: str | None = None,
    output_filename: str = None,
) -> list[dict]:

    results = []

    out_dir = None
    if output_directory:
        out_dir = Path(output_directory)
        out_dir.mkdir(parents=True, exist_ok=True)

    options = get_selenium_options(options_path, out_dir)
    chrome_options = options.get("chrome_options")

    result = {
        "url": url,
        "status": None,
        "html": None,
        "error": None,
    }

    try:
        driver = webdriver.Chrome(options=chrome_options)

        logger.info(f"Loading URL: {url}")
        driver.get(url)

        html = driver.page_source
        result["html"] = html
        result["status"] = 0

        driver.quit()

    except WebDriverException as e:
        logger.error(f"Selenium error: {e}")
        result["status"] = 1
        result["error"] = str(e)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        result["status"] = 1
        result["error"] = str(e)

    results.append(result)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Selenium downloader")
    parser.add_argument("url", type=str, help="URL to scrape")
    parser.add_argument("-o", "--options_path", default=None, type=str)
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Download directory"
    )

    args = parser.parse_args()

    results = download(
        url=args.url,
        options_path=args.options_path,
        output_directory=args.output_directory,
    )

    pp.pprint(results)
