import argparse
import os
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from downloaders.selector import _write_output
from utils.logger import setup_logger

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")


BY_MAP = {
    "css": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "id": By.ID,
    "name": By.NAME,
    "class": By.CLASS_NAME,
    "tag": By.TAG_NAME,
    "link_text": By.LINK_TEXT,
    "partial_link_text": By.PARTIAL_LINK_TEXT,
}


def run_events(driver, events: list, result: dict):
    results = {}

    def get_by(event):
        return BY_MAP.get(event.get("by", "css"), By.CSS_SELECTOR)

    def handle_get(event):
        driver.get(event["url"])

    def handle_quit(event):
        driver.quit()

    def handle_wait(event):
        WebDriverWait(driver, event.get("timeout", 10)).until(
            EC.presence_of_element_located((get_by(event), event["value"]))
        )

    def handle_click(event):
        driver.find_element(get_by(event), event["value"]).click()

    def handle_type(event):
        el = driver.find_element(get_by(event), event["value"])
        el.clear()
        el.send_keys(event.get("text", ""))

    def handle_submit(event):
        driver.find_element(get_by(event), event["value"]).submit()

    def handle_sleep(event):
        time.sleep(event.get("seconds", 1))

    def handle_execute_js(event):
        driver.execute_script(event.get("script", ""))

    def handle_extract(event):
        if event.get("value"):
            el = driver.find_element(get_by(event), event["value"])
            data = (
                el.get_attribute(event["attribute"])
                if event.get("attribute")
                else el.text
            )
        else:
            data = driver.page_source

        name = event.get("name", "extract")
        results.setdefault(name, []).append(data)

    def handle_extract_all(event):
        elements = driver.find_elements(get_by(event), event["value"])

        if event.get("attribute"):
            data = [el.get_attribute(event["attribute"]) for el in elements]
        else:
            data = [el.text for el in elements]

        name = event.get("name", "extract_all")
        results[name] = data

    def handle_extract_structured(event):
        parent_cfg = event["parent"]
        fields = event.get("fields", {})

        parent_by = BY_MAP.get(parent_cfg.get("by", "css"))
        parents = driver.find_elements(parent_by, parent_cfg["value"])

        structured_data = []

        for parent in parents:
            item = {}
            for field_name, field_cfg in fields.items():
                field_by = BY_MAP.get(field_cfg.get("by", "css"))
                try:
                    el = parent.find_element(field_by, field_cfg["value"])
                    item[field_name] = (
                        el.get_attribute(field_cfg["attribute"])
                        if field_cfg.get("attribute")
                        else el.text
                    )
                except Exception:
                    item[field_name] = None
            structured_data.append(item)

        name = event.get("name", "extract_structured")
        results[name] = structured_data

    def handle_save(event):
        filename = event.get("filename", "page.html")
        result = driver.page_source
        _write_output(result, filename)

    def handle_screenshot(event):
        driver.save_screenshot(event.get("path", "screenshot.png"))

    ACTIONS = {
        "get": handle_get,
        "quit": handle_quit,
        "wait": handle_wait,
        "click": handle_click,
        "type": handle_type,
        "submit": handle_submit,
        "sleep": handle_sleep,
        "execute_js": handle_execute_js,
        "extract": handle_extract,
        "extract_all": handle_extract_all,
        "extract_structured": handle_extract_structured,
        "save": handle_save,
        "screenshot": handle_screenshot,
    }

    for index, event in enumerate(events):
        action = event.get("action")

        if action not in ACTIONS:
            raise ValueError(f"[Event #{index}] Unknown action: {action}")

        try:
            ACTIONS[action](event)
        except Exception as e:
            raise RuntimeError(f"[Event #{index}] Failed → {event}\nError: {str(e)}")

    return results


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

    out_dir = Path(output_directory or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    options = get_selenium_options(options_path, out_dir)
    chrome_options = options.get("chrome_options")
    events = options.get("events")

    result = {
        "url": url,
        "status": None,
        "error": None,
    }

    path = os.path.join(output_directory, output_filename) if output_filename else None

    try:
        driver = webdriver.Chrome(options=chrome_options)

        logger.info(f"Loading URL: {url}")
        driver.get(url)

        if events:
            results = run_events(driver, events, result)
        else:
            result["status"] = 0
            result["progress"] = "100%"
            result["path"] = path
            results = [result]

        if path:
            _write_output(results, path)

        driver.quit()

    except WebDriverException as e:
        logger.error(f"Selenium error: {e}")
        result["status"] = 1
        result["error"] = str(e)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        result["status"] = 1
        result["error"] = str(e)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Selenium downloader")
    parser.add_argument("url", type=str, help="URL to scrape")
    parser.add_argument("-o", "--options_path", default=None, type=str)
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Download directory"
    )
    parser.add_argument(
        "-f",
        "--output_filename",
        type=str,
        default=None,
        help="Download filename",
    )
    args = parser.parse_args()

    results = download(
        url=args.url,
        options_path=args.options_path,
        output_directory=args.output_directory,
        output_filename=args.output_filename,
    )

    pp.pprint(results)
