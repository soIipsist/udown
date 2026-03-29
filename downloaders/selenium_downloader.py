import argparse
import os
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from utils.logger import setup_logger, write_output
import re
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import undetected_chromedriver as uc

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


class Event:

    _arguments: list = None
    _function_name: str = None
    _variable: str = None

    @property
    def variable(self):
        return self._variable

    @variable.setter
    def variable(self, variable):
        self._variable = variable

    @property
    def arguments(self):
        return self._arguments

    @arguments.setter
    def arguments(self, arguments):
        self._arguments = arguments

    @property
    def function_name(self):
        return self._function_name

    @function_name.setter
    def function_name(self, function_name: str):
        self._function_name = function_name

    def __init__(self, event: str):
        pass

    def parse_event(self, event: str):
        parts = event.split("=", 1)  # split once

        variable_part = parts[0].strip()
        function_part = parts[1].strip() if len(parts) > 1 else None

    # functions = {
    #     "e": self.driver.get_element,
    #     "e.name": self.driver.get_element_by_name,
    #     "e.id": self.driver.get_element_by_id,
    #     "e.class_name": self.driver.get_element_by_class_name,
    #     "e.selector": self.driver.get_element_by_selector,
    #     "e.link_text": self.driver.get_element_by_link_text,
    #     "e.partial_link_text": self.driver.get_element_by_partial_link_text,
    #     "e.clear": self.driver.clear_element,
    #     "c": self.driver.add_cookies,
    #     "cookies": self.driver.get_cookies,
    #     "delete_cookies": self.driver.delete_cookies,
    #     "delay": self.driver.add_delay,
    #     "wait": self.driver.add_implicit_wait,
    #     "explicit_wait": self.driver.add_explicit_wait,
    #     "js": self.driver.execute_script,
    #     "keys": self.driver.send_keys,
    #     "click": self.driver.click_element,
    #     "dnd": self.driver.drag_and_drop,
    #     "select": self.driver.select,
    #     "deselect": self.driver.deselect,
    # }

    @classmethod
    def get_function_name_and_arguments(cls, function_part: str):
        function_pattern = r"([\w_\.]+)(?:\(\s*([^\(\)]*)\s*\))?"

        match = re.match(function_pattern, function_part)

        function_name = None
        arguments = []

        if match:
            function_name = match.group(1)
            arguments = match.group(2)

            if not arguments:
                arguments = []
            else:
                argument_list = []
                argument = ""
                inside_array = False

                for char in arguments:
                    if char == "[":
                        inside_array = True
                        argument += char
                    elif char == "]":
                        inside_array = False
                        argument += char
                    elif char == "," and not inside_array:
                        argument_list.append(argument.strip())
                        argument = ""
                    else:
                        argument += char

                if argument:
                    argument_list.append(argument.strip())

                arguments = []
                for arg in argument_list:
                    arg = arg.strip().strip("'").strip('"')
                    if arg.startswith("[") and arg.endswith("]"):
                        elements = arg[1:-1].split(",")
                        elements = [
                            element.strip().strip("'").strip('"')
                            for element in elements
                        ]
                        arguments.append(elements)
                    else:
                        arguments.append(arg)

        return function_name, arguments


class SeleniumDriver:
    _driver_type = None
    _browser_type = None
    _events: list = None
    _browser_options = None
    _driver = None

    browser_types = {
        "chrome": webdriver.Chrome,
        "firefox": webdriver.Firefox,
        "edge": webdriver.Edge,
        "ie": webdriver.Ie,
        "safari": webdriver.Safari,
    }

    @property
    def browser_type(self):
        return self._browser_type

    @browser_type.setter
    def browser_type(self, browser_type):
        if isinstance(browser_type, str):
            if self.driver_type == "undetected":
                browser_type = uc.Chrome
            else:
                browser_type = self.browser_types.get(browser_type, webdriver.Chrome)

        self._browser_type = browser_type

    @property
    def driver(self):
        return self._driver

    @driver.setter
    def driver(self, driver):
        self._driver = driver

    @property
    def driver_type(self):
        return self._driver_type

    @driver_type.setter
    def driver_type(self, driver_type):
        self._driver_type = driver_type

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, events):
        self._events = events

    @property
    def browser_options(self):
        return self._browser_options

    @browser_options.setter
    def browser_options(self, browser_options):
        self._browser_options = browser_options

    def __init__(
        self,
        driver_type=webdriver,
        browser_type=webdriver.Chrome,
        browser_options=None,
        events: list = None,
    ):
        self.driver_type = driver_type
        self.browser_type = browser_type
        self.browser_options = browser_options
        self.events = events

    def get_driver_instance(self):

        self.driver = self.browser_type(options=self.browser_options)

        return self.driver


def execute_events(
    driver, events: list, base_result: dict, save_path: str | None = None
):
    emitted_results = []

    def build_result(path):
        filename = os.path.basename(path)
        return {
            "url": base_result["url"],
            "status": 0,
            "error": None,
            "progress": "100%",
            "output_filename": (filename if filename else None),
            "path": path,
        }

    def get_by(event):
        return BY_MAP.get(event.get("by", "css"), By.CSS_SELECTOR)

    def write_and_record(content, path):
        write_output(logger, content, path)
        emitted_results.append(build_result(path))

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

        path = event.get("filename", save_path)
        if not path:
            return

        write_and_record(data, path)

    def handle_extract_all(event):
        elements = driver.find_elements(get_by(event), event["value"])

        if event.get("attribute"):
            data = [el.get_attribute(event["attribute"]) for el in elements]
        else:
            data = [el.text for el in elements]

        path = event.get("filename", save_path)
        if not path:
            return

        write_and_record(data, path)

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

        path = event.get("filename", save_path)
        if not path:
            return

        write_and_record(structured_data, path)

    def handle_save(event):
        path = event.get("filename", "page.html")
        write_and_record(driver.page_source, path)

    def handle_screenshot(event):
        path = event.get("path", "screenshot.png")
        driver.save_screenshot(path)
        emitted_results.append(build_result(path))

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
            emitted_results.append(
                {
                    "url": base_result["url"],
                    "status": 1,
                    "error": f"[Event #{index}] Failed → {event}\nError: {str(e)}",
                    "progress": "100%",
                    "path": None,
                }
            )

    return emitted_results


def get_chrome_options(
    options: dict, output_directory: Path | None = None
) -> webdriver.ChromeOptions:
    chrome_options = webdriver.ChromeOptions()

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
            results = execute_events(driver, events, result, path)
        else:
            result["status"] = 0
            result["progress"] = "100%"
            result["path"] = path
            results = [result]

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
