import os
import re
import json
import requests
from bs4 import BeautifulSoup

from utils.logger import setup_logger

logger = setup_logger(name="bs4", log_dir="/udown/bs4")


def _write_output(result, path: str = None):
    
    if path is None:
        logger.info(f"Result: {result}")
        return
    
    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    else:
        # default: text
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(result, (list, tuple)):
                for item in result:
                    f.write(f"{item}\n")
            else:
                f.write(str(result))
                
    logger.info(f"Saved extraction results to {path}")


def extract(
    url: str,
    selector: str,
    attribute: str = None,
    output_directory: str = None,
    output_filename: str = None,
):
    """
    Extract values from HTML using BeautifulSoup.
    """

    if not selector:
        return {"status": 1, "result": [], "output_path": None}

    logger.info(f"Extracting selector='{selector}' attribute='{attribute}'")

    try:
        if re.match(r"^https?://", url):
            response = requests.get(url)
            response.raise_for_status()
            html = response.text
        else:
            html = url
    except Exception:
        logger.exception("Failed to load HTML")
        return {"status": 1, "result": [], "output_path": None}

    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(selector)

    result = [
        elem.get(attribute) if attribute else elem.get_text(strip=True)
        for elem in elements
    ]

    path = None

    if not output_directory:
        output_directory = os.getcwd()
    
    try:
        os.makedirs(output_directory, exist_ok=True)
        path = os.path.join(output_directory, output_filename) if output_filename else None
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
