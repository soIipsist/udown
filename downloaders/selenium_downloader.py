import argparse
import os
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from src.options import DOWNLOADER_METADATA_DIR
from utils.logger import setup_logger, write_output
import re
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import DesiredCapabilities
import undetected_chromedriver as uc

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")

driver_instance = None

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


driver_types = {
    "chrome": webdriver.Chrome,
    "edge": webdriver.Edge,
    "firefox": webdriver.Firefox,
    "safari": webdriver.Safari,
    "ie": webdriver.Ie,
}

browser_option_types = {
    "chrome": webdriver.ChromeOptions,
    "edge": webdriver.EdgeOptions,
    "firefox": webdriver.FirefoxOptions,
    "safari": webdriver.SafariOptions,
    "ie": webdriver.IeOptions,
}

capability_types = {
    "chrome": DesiredCapabilities.CHROME.copy(),
    "edge": DesiredCapabilities.EDGE.copy(),
    "firefox": DesiredCapabilities.FIREFOX.copy(),
    "safari": DesiredCapabilities.SAFARI.copy(),
    "ie": DesiredCapabilities.INTERNETEXPLORER.copy(),
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


class BrowserOptions:
    _browser_options_type = None
    _browser_options_obj = None
    _default_capabilities = None

    def __init__(self, driver_type=None, browser_type="chrome", browser_args=None):
        if driver_type == "undetected":
            self.browser_options_type = uc.options.ChromeOptions
        else:
            self.browser_options_type = browser_option_types.get(
                browser_type, webdriver.ChromeOptions
            )

        self.browser_args = browser_args

    @property
    def browser_options_type(self):
        return self._browser_options_type

    @browser_options_type.setter
    def browser_options_type(self, browser_options_type):
        self._browser_options_type = browser_options_type

    @property
    def browser_options_obj(self):
        return self._browser_options_obj

    @browser_options_obj.setter
    def browser_options_obj(self, browser_options_obj):
        self._browser_options_obj = browser_options_obj

    @property
    def default_capabilities(self):
        return self._default_capabilities

    @default_capabilities.setter
    def default_capabilities(self, default_capabilities):
        self._default_capabilities = default_capabilities

    def add_arguments(self, arguments: list = None):
        if not hasattr(self.browser_options_obj, "add_argument") or not arguments:
            return

        logger.info(f"Arguments: {arguments}.")

        for argument in arguments:
            if argument not in self.browser_options_obj.arguments:
                self.browser_options_obj.add_argument(argument)

    def add_experimental_options(self, experimental_options: dict = None):
        if (
            not hasattr(self.browser_options_obj, "add_experimental_option")
            or not isinstance(experimental_options, dict)
            or not experimental_options
        ):
            return

        logger.info(f"Experimental options: {experimental_options}.")

        for name, value in experimental_options.items():
            self.browser_options_obj.add_experimental_option(name, value)

    def add_additional_options(self, additional_options: dict = None):
        if (
            not hasattr(self.browser_options_obj, "add_additional_option")
            or not isinstance(additional_options, dict)
            or not additional_options
        ):
            return

        logger.info(f"Additional options: {additional_options}.")

        for name, value in additional_options.items():
            self.browser_options_obj.add_additional_option(name, value)

    def set_capabilities(self, capabilities: dict = None):

        if (
            not hasattr(self.browser_options_obj, "set_capability")
            or not isinstance(capabilities, dict)
            or not capabilities
        ):
            return

        logger.info(f"Setting browser capabilities: {capabilities}.")
        for name, value in capabilities.items():
            self.browser_options_obj.set_capability(name, value)

    def set_preferences(self, preferences: dict = None):
        if (
            not hasattr(self.browser_options_obj, "set_preference")
            or not isinstance(preferences, dict)
            or not preferences
        ):
            return

        logger.info(f"Preferences: {preferences}.")

        for name, value in preferences.items():
            self.browser_options_obj.set_preference(name, value)

    def get_browser_options(self):
        self.browser_options_obj = self.browser_options_type()

        preferences = self.browser_args.get("preferences")
        capabilities = self.browser_args.get("capabilities")
        experimental_options = self.browser_args.get("experimental_options")
        additional_options = self.browser_args.get("additional_options")
        arguments = self.browser_args.get("arguments")

        self.set_capabilities(capabilities)
        self.add_experimental_options(experimental_options)
        self.set_preferences(preferences)
        self.add_additional_options(additional_options)
        self.add_arguments(arguments)
        return self.browser_options_obj


class SeleniumDriver:
    _driver_type = None
    _browser_type = None
    _events: list = None
    _browser_options = None
    _driver = None

    @property
    def browser_type(self):
        return self._browser_type

    @browser_type.setter
    def browser_type(self, browser_type):
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

    def get_driver_type(self):
        return (
            uc.Chrome
            if self.driver_type == "undetected"
            else driver_types.get(self.browser_type, webdriver.Chrome)
        )

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

    @property
    def browser_options_instance(self) -> BrowserOptions:
        return BrowserOptions(
            self.driver_type,
            self.browser_type,
            self.browser_options,
        )

    def __init__(
        self,
        driver_type=None,
        browser_type=webdriver.Chrome,
        browser_options=None,
        events: list = None,
    ):
        self.driver_type = driver_type
        self.browser_type = browser_type
        self.browser_options = browser_options
        self.events = events

    def get_driver_instance(self):

        browser_options = self.browser_options_instance.get_browser_options()

        if not self.driver:
            self.driver = self.get_driver_type()(options=browser_options)

        return self.driver

    def execute_events(self, base_result: dict, save_path: str | None = None):
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
            self.driver.get(event["url"])

        def handle_quit(event):
            self.driver.quit()

        def handle_wait(event):
            WebDriverWait(self.driver, event.get("timeout", 10)).until(
                EC.presence_of_element_located((get_by(event), event["value"]))
            )

        def handle_click(event):
            self.driver.find_element(get_by(event), event["value"]).click()

        def handle_type(event):
            el = self.driver.find_element(get_by(event), event["value"])
            el.clear()
            el.send_keys(event.get("text", ""))

        def handle_submit(event):
            self.driver.find_element(get_by(event), event["value"]).submit()

        def handle_sleep(event):
            time.sleep(event.get("seconds", 1))

        def handle_execute_js(event):
            self.driver.execute_script(event.get("script", ""))

        def handle_extract(event):
            if event.get("value"):
                el = self.driver.find_element(get_by(event), event["value"])
                data = (
                    el.get_attribute(event["attribute"])
                    if event.get("attribute")
                    else el.text
                )
            else:
                data = self.driver.page_source

            path = event.get("filename", save_path)
            if not path:
                return

            write_and_record(data, path)

        def handle_extract_all(event):
            elements = self.driver.find_elements(get_by(event), event["value"])

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
            parents = self.driver.find_elements(parent_by, parent_cfg["value"])

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
            write_and_record(self.driver.page_source, path)

        def handle_screenshot(event):
            path = event.get("path", "screenshot.png")
            self.driver.save_screenshot(path)
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

        for index, event in enumerate(self.events):
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


def get_selenium_options(options_path: str = None):
    if not options_path or not os.path.exists(options_path):
        options_path = os.path.join(DOWNLOADER_METADATA_DIR, "selenium.json")

    logger.info(f"Using selenium options from path: {options_path}")
    options = read_json_file(options_path)

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

    options = get_selenium_options(options_path)

    if output_directory:
        if options["preferences"]:
            options["preferences"].update(
                {
                    "download.default_directory": str(output_directory.resolve()),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True,
                }
            )
    selenium_driver = SeleniumDriver(**options)

    result = {
        "url": url,
        "status": None,
        "error": None,
    }

    path = os.path.join(output_directory, output_filename) if output_filename else None

    try:
        results = selenium_driver.execute_events(result, save_path=path)

        if selenium_driver.driver:
            selenium_driver.driver.quit()

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
