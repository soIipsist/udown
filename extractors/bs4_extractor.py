import argparse
import requests
from bs4 import BeautifulSoup
import re


def extract(url, selector, attribute=None, multiple=True):

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
        return [] if multiple else None

    results = []
    for elem in elements:
        value = elem.get(attribute) if attribute else elem.get_text(strip=True)
        results.append(value)

    return results if multiple else results[0]


def main():
    parser = argparse.ArgumentParser(description="Generic BeautifulSoup extractor")
    parser.add_argument("url", help="URL (http/https) or raw HTML string/file path")
    parser.add_argument("--selector", required=True, help="CSS selector to extract")
    parser.add_argument("--attribute", help="Attribute to extract (e.g., href, src)")
    parser.add_argument(
        "--single", action="store_true", help="Return only the first match"
    )
    parser.add_argument(
        "--file", action="store_true", help="Treat url as path to local HTML file"
    )

    args = parser.parse_args()

    content = args.url
    if args.file:
        with open(content, "r", encoding="utf-8") as f:
            content = f.read()

    try:
        results = extract(
            url=content,
            selector=args.selector,
            attribute=args.attribute,
            multiple=not args.single,
        )
        if isinstance(results, list):
            for r in results:
                print(r)
        else:
            print(results)
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
