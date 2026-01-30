import argparse
from pprint import PrettyPrinter
import requests
from bs4 import BeautifulSoup
import re

from utils.logger import setup_logger

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="bs4", log_dir="/udown/bs4")


def extract(
    url,
    selector,
    attribute=None,
    output_directory: str = None,
    output_filename: str = None,
):
    results = []

    if not selector:
        raise ValueError("CSS selector is required.")

    if re.match(r"^https?://", url):
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    else:
        soup = BeautifulSoup(url, "html.parser")

    elements = soup.select(selector)

    if not elements:
        return []

    for elem in elements:
        value = elem.get(attribute) if attribute else elem.get_text(strip=True)
        results.append(value)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic BeautifulSoup extractor")
    parser.add_argument("url", help="URL (http/https) or raw HTML string/file path")
    parser.add_argument(
        "-s", "--selector", required=True, help="CSS selector to extract"
    )
    parser.add_argument(
        "-a", "--attribute", help="Attribute to extract (e.g., href, src)"
    )
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )
    parser.add_argument(
        "-f", "--output_filename", type=str, default=None, help="Custom output filename"
    )

    args = parser.parse_args()

    try:
        results = extract(
            url=args.url,
            selector=args.selector,
            attribute=args.attribute,
        )
        if isinstance(results, list):
            for r in results:
                print(r)
        else:
            print(results)
    except Exception as e:
        print("Error:", e)
