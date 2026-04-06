import argparse
import json
import os
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from src.options import DOWNLOADER_METADATA_DIR
from utils import read_file
from utils.logger import setup_logger, write_output
import re
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import time
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
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


class SeleniumDownloader:
    _driver_type = None
    _browser_type = None
    _events: list = None
    _event_variables: dict = {}
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
    def event_variables(self):
        return self._event_variables

    @event_variables.setter
    def event_variables(self, event_variables: dict):
        self._event_variables = event_variables

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

    def get(self, url: str):

        if not self.driver:
            self.driver = self.get_driver_instance()

        self.driver.get(url)

    def quit(self):
        if self.driver:
            self.driver.quit()

    def extract(self, value: str = None, attribute: str = None, by: str = None):
        if value:
            el = self.get_element(value, by)
            data = el.get_attribute(attribute) if attribute else el.text
        else:
            data = self.driver.page_source
        return data

    def extract_all(self, value: str = None, attribute: str = None, by: str = None):
        if value:
            elements = self.get_elements(value, by)
            data = [
                el.get_attribute(attribute) if attribute else el.text for el in elements
            ]
        else:
            data = self.driver.page_source

        return data

    def get_element(self, value: str, by: str = None):
        if by is None:
            by = "xpath"

        element = None

        try:
            element = self.driver.find_element(by=by, value=value)
        except Exception as e:
            print(e)

        return element

    def get_elements(self, value: str, by: str = None):
        if by is None:
            by = "xpath"

        elements = []

        try:
            elements = self.driver.find_elements(by=by, value=value)
        except Exception as e:
            print(e)

        return elements

    def get_locator(self, by: str, value: str):
        return (by, value)

    def get_element_by_xpath(self, xpath: str):
        return self.get_element(by=By.XPATH, value=xpath)

    def get_element_by_id(self, id: str):
        return self.get_element(by=By.ID, value=id)

    def get_element_by_name(self, name: str):
        return self.get_element(by=By.NAME, value=name)

    def get_element_by_link_text(self, link_text: str):
        return self.get_element(by=By.LINK_TEXT, value=link_text)

    def get_element_by_partial_link_text(self, partial_link_text: str):
        return self.get_element(by=By.PARTIAL_LINK_TEXT, value=partial_link_text)

    def get_element_by_tag_name(self, tag_name: str):
        return self.get_element(by=By.TAG_NAME, value=tag_name)

    def get_element_by_class_name(self, class_name: str):
        return self.get_element(by=By.TAG_NAME, value=class_name)

    def get_element_by_selector(self, selector: str):
        return self.get_element(by=By.CSS_SELECTOR, value=selector)

    def get_elements_by_xpath(self, xpath: str):
        return self.get_elements(by=By.XPATH, value=xpath)

    def get_elements_by_id(self, id: str):
        return self.get_elements(by=By.ID, value=id)

    def get_elements_by_name(self, name: str):
        return self.get_elements(by=By.NAME, value=name)

    def get_elements_by_link_text(self, link_text: str):
        return self.get_elements(by=By.LINK_TEXT, value=link_text)

    def get_elements_by_partial_link_text(self, partial_link_text: str):
        return self.get_elements(by=By.PARTIAL_LINK_TEXT, value=partial_link_text)

    def get_elements_by_tag_name(self, tag_name: str):
        return self.get_elements(by=By.TAG_NAME, value=tag_name)

    def get_elements_by_class_name(self, class_name: str):
        return self.get_elements(by=By.TAG_NAME, value=class_name)

    def get_elements_by_selector(self, selector: str):
        return self.get_elements(by=By.CSS_SELECTOR, value=selector)

    def send_keys(self, element: WebElement, keys: str):
        if element and isinstance(element, WebElement):
            element.send_keys(keys)

    def click_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            element.click()

    def submit_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            element.submit()

    def sleep(self, seconds: float):
        time.sleep(seconds)

    def clear_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            element.clear()

    def add_cookies(self, cookies: list):

        for cookie in cookies:
            if isinstance(cookie, dict):
                self.driver.add_cookie(cookie)
        return cookies

    def drag_and_drop(self, element: WebElement, target: WebElement):
        action_chains = ActionChains(self.driver)
        action_chains.drag_and_drop(element, target).perform()

    def take_screenshot(self, path: str = None):
        if not path:
            path = "screenshot.png"
        self.driver.save_screenshot(path)

    def execute_script(self, script: str, asynchronous=False):
        if os.path.exists(script):
            script = read_file(script, logger=logger)

        if asynchronous:
            result = self.driver.execute_async_script(script)
        else:
            result = self.driver.execute_script(script)

        return result

    def add_explicit_wait(
        self, delay: int = 10, ec_function: str = None, *args, **kwargs
    ):
        ec_function = EC.__dict__.get(ec_function, "presence_of_element_located")
        result = None

        wait = WebDriverWait(self.driver, delay)
        result = wait.until(ec_function(*args))
        return result

    def add_implicit_wait(self, delay: float):
        self.driver.implicitly_wait(delay)

    def add_delay(self, delay: float):
        time.sleep(delay)

    def get_cookies(self, cookie: str = None):
        return (
            self.driver.get_cookies() if not cookie else self.driver.get_cookie(cookie)
        )

    def delete_cookies(self, cookie: str = None):
        return (
            self.driver.delete_all_cookies()
            if not cookie
            else self.driver.delete_cookie(cookie)
        )

    def select(self, select_element: WebElement, value: int):
        if select_element and isinstance(select_element, WebElement):
            select = Select(select_element)
            if isinstance(value, int):
                select.select_by_index(value)
            else:
                select.select_by_value(value)

    def deselect(self, select_element: WebElement):
        if select_element and isinstance(select_element, WebElement):
            select = Select(select_element)
            select.deselect_all()

    def switch_to(self, element: str, *args, **kwargs):
        result = None

        if hasattr(self.driver.switch_to, element):
            attr = getattr(self.driver.switch_to, element)
            if callable(attr):
                result = attr(**kwargs)
            else:
                result = attr
        return result

    def save(self, path: str):
        if not path:
            path = "page.html"
        write_output(logger, self.driver.page_source, path, False)

    def get_network_traffic(self):
        requests = []
        responses = []

        if hasattr(self.driver, "get_log"):

            try:
                logs = self.driver.get_log("performance")

                for log in logs:
                    message = json.loads(log["message"])
                    message_data = message["message"]["params"]

                    if "request" in message_data:
                        request = message_data["request"]
                        requests.append(request)
                    elif "response" in message_data:
                        response = message_data["response"]
                        responses.append(response)
            except Exception as e:
                print(e)

        return requests, responses

    # events stuff
    def parse_event(self, event: str):
        if isinstance(event, dict):
            return event

        parts = event.split("=", 1)  # split once

        variable_part = parts[0].strip()
        action_part = parts[1].strip() if len(parts) > 1 else None

        if not action_part:
            action_part = variable_part
            variable_part = None

        action, arguments = self.get_action_and_arguments(action_part)

        event_dict = {
            "variable": variable_part,
            "action": action,
            "arguments": arguments,
        }

        return event_dict

    def get_action_and_arguments(self, action_part: str):
        action_pattern = r"([\w_\.]+)(?:\(\s*([^\(\)]*)\s*\))?"

        match = re.match(action_pattern, action_part)

        action = None
        arguments = []

        if match:
            action = match.group(1)
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

        return action, arguments

    def execute_events(self, url: str = None, save_path: str | None = None):
        emitted_results = []

        def build_result(path):
            filename = os.path.basename(path)
            return {
                "url": url,
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

        ACTIONS = {
            "get": self.get,
            "quit": self.quit,
            "e": self.get_element,
            "e.name": self.get_element_by_name,
            "e.id": self.get_element_by_id,
            "e.class_name": self.get_element_by_class_name,
            "e.selector": self.get_element_by_selector,
            "e.link_text": self.get_element_by_link_text,
            "e.partial_link_text": self.get_element_by_partial_link_text,
            "e.clear": self.clear_element,
            "c": self.add_cookies,
            "cookies": self.get_cookies,
            "add_cookies": self.add_cookies,
            "delete_cookies": self.delete_cookies,
            "delay": self.add_delay,
            "js": self.execute_script,
            "keys": self.send_keys,
            "click": self.click_element,
            "dnd": self.drag_and_drop,
            "select": self.select,
            "deselect": self.deselect,
            "wait": self.add_implicit_wait,
            "implicit_wait": self.add_implicit_wait,
            "explicit_wait": self.add_explicit_wait,
            "click": self.click_element,
            "type": self.send_keys,
            "submit": self.submit_element,
            "sleep": self.sleep,
            "extract": self.extract,
            "extract_all": self.extract_all,
            "save": self.save,
            "screenshot": self.take_screenshot,
        }

        for index, event in enumerate(self.events):

            event = self.parse_event(event)

            action = event.get("action")

            if action not in ACTIONS:
                raise ValueError(f"[Event #{index}] Unknown action: {action}")

            try:
                ACTIONS[action](*event)
            except Exception as e:
                emitted_results.append(
                    {
                        "url": url,
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


def has_get_event(events):
    return any(
        (isinstance(e, str) and "get" in e)
        or (isinstance(e, dict) and e.get("action") == "get")
        for e in events
    )


def download(
    url: str,
    options_path: str | None = None,
    output_directory: str | None = None,
    output_filename: str = None,
) -> list[dict]:

    results = []

    out_dir = Path(output_directory or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if os.path.exists(url):  # use url argument as options path
        options = get_selenium_options(url)
    else:
        options = get_selenium_options(options_path)

        # insert get event, in case it doesn't already exist
        events = options.get("events", [])
        events: list

        if not has_get_event(events):
            events.insert(0, f"response = get({url})")
            options["events"] = events

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
    selenium_downloader = SeleniumDownloader(**options)

    result = {
        "url": url,
        "status": None,
        "error": None,
    }

    path = os.path.join(output_directory, output_filename) if output_filename else None

    try:
        results = selenium_downloader.execute_events(url, save_path=path)

        if selenium_downloader.driver:
            selenium_downloader.driver.quit()

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
