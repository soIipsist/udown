import argparse
import os
from pprint import pp
import re
import requests
from downloaders.bs4 import _write_output, apply_rules
from lxml import html as lxml_html
from utils.logger import setup_logger

logger = setup_logger(name="lxml", log_dir="/udown/lxml")

def extract_xpath(
    url: str,
    xpath: str,
    output_directory: str = None,
    output_filename: str = None,
    rules: list = None,
):
    """
    Extract values from HTML using XPath.
    """

    if not xpath:
        return {"status": 1, "result": [], "output_path": None}

    logger.info(f"Extracting xpath='{xpath}'")

    try:
        if re.match(r"^https?://", url):
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.text
        else:
            html_content = url
    except Exception:
        logger.exception("Failed to load HTML")
        return {"status": 1, "result": [], "output_path": None}

    try:
        tree = lxml_html.fromstring(html_content)
        elements = tree.xpath(xpath)
    except Exception:
        logger.exception("Invalid XPath expression")
        return {"status": 1, "result": [], "output_path": None}

    result = []
    for elem in elements:
        if isinstance(elem, lxml_html.HtmlElement):
            result.append(elem.text_content().strip())
        else:
            # XPath can return strings, numbers, attrs, etc.
            result.append(str(elem).strip())

    result = apply_rules(url, result, rules)

    path = None
    if not output_directory:
        output_directory = os.getcwd()

    try:
        os.makedirs(output_directory, exist_ok=True)
        path = (
            os.path.join(output_directory, output_filename)
            if output_filename
            else None
        )
        _write_output(result, path)
    except Exception as e:
        logger.error(f"Exception: {e}")
        return {"status": 1, "result": result, "output_path": None}

    return {
        "status": 0,
        "result": result,
        "output_path": path,
        "output_directory": output_directory,
        "output_filename": output_filename,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract values from HTML using BeautifulSoup."
    )
    parser.add_argument("url", type=str, help="Target URL")
    parser.add_argument("-x","--xpath", type=str, help="XPath", default="//a/@href")
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )
    parser.add_argument("-f", "--output_filename", type=str, default=None, help="Save filename")
    parser.add_argument("-r", "--rules", type=str, default=None)
    args = parser.parse_args()

    results = extract_xpath(
        args.url,
        args.xpath,
        args.output_directory,
        args.output_filename,
        args.rules
    )

    pp.pprint(results)
