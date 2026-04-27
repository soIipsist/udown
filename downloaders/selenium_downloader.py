import argparse
import ast
import json
import os
from pathlib import Path
from pprint import PrettyPrinter
from downloaders.ytdlp import read_json_file
from src.options import DOWNLOADER_METADATA_DIR, get_option
from utils import read_file, is_valid_url
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

uc.TARGET_VERSION = 78

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="selenium_downloader", log_dir="/udown/selenium")

driver_instance = None


driver_types = {
    "uc": uc.Chrome,
    "chrome": webdriver.Chrome,
    "edge": webdriver.Edge,
    "firefox": webdriver.Firefox,
    "safari": webdriver.Safari,
    "ie": webdriver.Ie,
}

browser_option_types = {
    "uc": uc.options.ChromeOptions,
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
    _browser_type = None
    _proxy: str = None
    _user_agent: str = None
    _output_directory: str = None

    def __init__(
        self,
        browser_type="chrome",
        browser_args=None,
        output_directory: str = None,
        proxy: str = None,
        user_agent: str = None,
    ):

        self.browser_type = browser_type
        self.browser_options_type = browser_option_types.get(
            browser_type, webdriver.ChromeOptions
        )
        self.browser_args = browser_args
        self.output_directory = output_directory
        self.proxy = proxy
        self.user_agent = user_agent

    @property
    def output_directory(self):
        return self._output_directory

    @output_directory.setter
    def output_directory(self, output_directory: str):
        self._output_directory = output_directory

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: str):
        self._proxy = proxy

    @property
    def user_agent(self):
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent: str):
        self._user_agent = user_agent

    @property
    def browser_type(self):
        return self._browser_type

    @browser_type.setter
    def browser_type(self, browser_type):
        self._browser_type = browser_type

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

    def set_output_directory(self):
        if not self.output_directory:
            return

        if not self.browser_args.get("preferences"):
            self.browser_args["preferences"] = {}

        if not self.browser_args.get("experimental_options"):
            self.browser_args["experimental_options"] = {}

        if self.browser_type in {"chrome", "edge", "uc"}:

            self.browser_args["experimental_options"].update(
                {
                    "prefs": {
                        "download.default_directory": self.output_directory,
                        "download.prompt_for_download": False,
                        "download.directory_upgrade": True,
                        "safebrowsing.enabled": False,
                        "safebrowsing.disable_download_protection": True,
                    }
                }
            )
        elif self.browser_type == "firefox":
            self.browser_args["preferences"].update(
                {
                    "browser.download.dir": self.output_directory,
                    "browser.download.folderList": 2,  # use custom dir
                    "browser.download.useDownloadDir": True,
                    "browser.helperApps.neverAsk.saveToDisk": (
                        "application/pdf,"
                        "application/octet-stream,"
                        "application/vnd.ms-excel,"
                        "text/csv,"
                        "application/zip"
                    ),
                    "pdfjs.disabled": True,  # force download PDFs
                }
            )
        elif self.browser_type == "safari":

            logger.error(
                "Safari does not support programmatic download directory control"
            )

        elif self.browser_type == "ie":
            logger.error("IE does not support download directory configuration")

    def set_proxy(self):
        pass

    def get_browser_options(self):
        self.browser_options_obj = self.browser_options_type()

        self.set_output_directory()
        self.set_proxy()

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
    _browser_type = None
    _events: list = None
    _event_outputs: dict = {}
    _browser_options = None
    _driver = None
    _output_filename = None
    _output_directory = None
    _url = None
    _results: list = []
    _result = None
    _proxy: str = None
    _user_agent: str = None

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: str):
        self._proxy = proxy

    @property
    def user_agent(self):
        return self._user_agent

    @user_agent.setter
    def user_agent(self, user_agent: str):
        self._user_agent = user_agent

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, result):
        self._result = result

    @property
    def results(self):
        return self._results

    @results.setter
    def results(self, results: list):
        self._results = results

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url: str):
        self._url = url

    @property
    def output_directory(self):
        return self._output_directory

    @output_directory.setter
    def output_directory(self, output_directory: str):
        self._output_directory = output_directory

    @property
    def output_path(self):
        return (
            os.path.join(self.output_directory, self.output_filename)
            if self.output_filename
            else self.output_directory
        )

    @property
    def output_filename(self):
        return self._output_filename

    @output_filename.setter
    def output_filename(self, output_filename: str):
        self._output_filename = output_filename

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

    def get_driver_type(self):
        return driver_types.get(self.browser_type, webdriver.Chrome)

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
            self.browser_type,
            self.browser_options,
            self.output_directory,
            self.proxy,
            self.user_agent,
        )

    @property
    def event_outputs(self):
        return self._event_outputs

    @event_outputs.setter
    def event_outputs(self, event_outputs: dict):
        self._event_outputs = event_outputs

    def __init__(
        self,
        browser_type=webdriver.Chrome,
        browser_options=None,
        events: list = None,
        url: str = None,
        output_directory: str = None,
        proxy: str = None,
        user_agent: str = None,
    ):
        self.browser_type = browser_type
        self.browser_options = browser_options
        self.events = events
        self.url = url
        self.output_directory = output_directory
        self.proxy = proxy
        self.user_agent = user_agent

    def get_driver_instance(self):

        browser_options = self.browser_options_instance.get_browser_options()

        if not self.driver:
            driver_type = self.get_driver_type()
            self.driver = driver_type(options=browser_options)

        return self.driver

    def get(self, url: str):

        if not self.driver:
            self.driver = self.get_driver_instance()

        self.url = url
        self.driver.get(url)

    def quit(self):
        if self.driver:
            self.driver.quit()

    def extract(
        self,
        value: str = None,
        attribute: str = None,
        by: str = None,
        output_filename: str = "output.json",
    ):
        if value:
            el = self.get_element(value, by)
            data = el.get_attribute(attribute) if attribute else el.text
        else:
            data = self.driver.page_source

        self.output_filename = output_filename
        write_output(logger, data, self.output_path, False)

        self.result = self.build_result()
        return data

    def extract_structured(
        self,
        value: str,
        key: str = "value",
        attribute: str = None,
        by: str = None,
        output_filename: str = "output.json",
        append: bool = False,
    ):
        structured_data = {}

        elements = self.get_elements(value, by, True)
        elements = [
            el.get_attribute(attribute) if attribute else el.text for el in elements
        ]
        structured_data.update({key: self.parse_data(elements)})
        return self.save(structured_data, output_filename, append)

    def extract_all(
        self,
        value: str = None,
        attribute: str = None,
        by: str = None,
        output_filename: str = "output.json",
    ):
        if value:
            elements = self.get_elements(value, by)
            data = [
                el.get_attribute(attribute) if attribute else el.text for el in elements
            ]
        else:
            data = self.driver.page_source

        self.output_filename = output_filename
        write_output(logger, data, self.output_path, False)

        self.result = self.build_result()
        return data

    def get_elements(self, value: str, by: str = None, return_multiple: bool = False):
        if by is None:
            by = "xpath"

        elements = None

        try:
            elements = (
                self.driver.find_elements(by=by, value=value)
                if return_multiple
                else self.driver.find_element(by=by, value=value)
            )
        except Exception as e:
            print(e)

        logger.info(f"Extracted elements: {elements}")
        return elements

    def get_locator(self, by: str, value: str):
        return (by, value)

    def get_elements_by_xpath(self, xpath: str, return_multiple: bool = False):
        return self.get_elements(
            by=By.XPATH, value=xpath, return_multiple=return_multiple
        )

    def get_elements_by_id(self, id: str, return_multiple: bool = False):
        return self.get_elements(by=By.ID, value=id, return_multiple=return_multiple)

    def get_elements_by_name(self, name: str, return_multiple: bool = False):
        return self.get_elements(
            by=By.NAME, value=name, return_multiple=return_multiple
        )

    def get_elements_by_link_text(self, link_text: str, return_multiple: bool = False):
        return self.get_elements(
            by=By.LINK_TEXT, value=link_text, return_multiple=return_multiple
        )

    def get_elements_by_partial_link_text(
        self, partial_link_text: str, return_multiple: bool = False
    ):
        return self.get_elements(
            by=By.PARTIAL_LINK_TEXT,
            value=partial_link_text,
            return_multiple=return_multiple,
        )

    def get_elements_by_tag_name(self, tag_name: str, return_multiple: bool = False):
        return self.get_elements(
            by=By.TAG_NAME, value=tag_name, return_multiple=return_multiple
        )

    def get_elements_by_class_name(
        self, class_name: str, return_multiple: bool = False
    ):
        return self.get_elements(
            by=By.CLASS_NAME, value=class_name, return_multiple=return_multiple
        )

    def get_elements_by_selector(self, selector: str, return_multiple: bool = False):
        return self.get_elements(
            by=By.CSS_SELECTOR, value=selector, return_multiple=return_multiple
        )

    def send_keys(self, element: WebElement, keys: str):
        if element and isinstance(element, WebElement):
            logger.info(f"Sent keys to element: {element}")
            element.send_keys(keys)

    def click_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            logger.info(f"Clicked element: {element}")
            element.click()

    def submit_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            logger.info(f"Submitted element: {element}")
            element.submit()

    def sleep(self, seconds: float):
        time.sleep(seconds)

    def clear_element(self, element: WebElement):
        if element and isinstance(element, WebElement):
            logger.info(f"Cleared element: {element}")
            element.clear()

    def add_cookies(self, cookies: list):

        for cookie in cookies:
            if isinstance(cookie, dict):
                self.driver.add_cookie(cookie)

        logger.info(f"Cookies: {cookies}")

        return cookies

    def drag_and_drop(self, element: WebElement, target: WebElement):
        action_chains = ActionChains(self.driver)
        action_chains.drag_and_drop(element, target).perform()

    def take_screenshot(self, filename: str = None):
        self.output_filename = "screenshot.png" if not filename else filename
        self.driver.save_screenshot(self.output_path)
        self.result = self.build_result()

        logger.info(f"Saved screenshot: {self.output_path}")

    def execute_script(self, script: str, asynchronous=False):
        if os.path.exists(script):
            script = read_file(script, logger=logger)

        logger.info(f"Executing script: {script}")

        if asynchronous:
            result = self.driver.execute_async_script(script)
        else:
            result = self.driver.execute_script(script)

        return result

    def add_explicit_wait(
        self, delay: int = 10, ec_function: str = None, *args, **kwargs
    ):
        logger.info(f"Explicit wait: {ec_function}, {delay}")
        ec_function = EC.__dict__.get(ec_function, "presence_of_element_located")
        result = None

        wait = WebDriverWait(self.driver, delay)
        result = wait.until(ec_function(*args))
        return result

    def add_implicit_wait(self, delay: float):
        logger.info(f"Implicit wait: {delay}")
        self.driver.implicitly_wait(delay)

    def add_delay(self, delay: float):
        logger.info(f"Adding delay: {delay}")
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

    def save(self, data=None, output_filename: str = None, append: bool = False):

        if not output_filename:
            ext = "html" if not data else "json"
            output_filename = f"output.{ext}"
        else:
            # get extension
            ext = os.path.splitext(output_filename)[1]
            ext = ext.lstrip(".")

        self.output_filename = output_filename

        if not data and ext == "html":
            data = self.driver.page_source

        self.result = self.build_result()

        data = self.parse_data(data)
        write_output(logger, data, self.output_path, append)

        return data

    def parse_item(self, item):
        if isinstance(item, WebElement):
            item = item.text

        return item

    def parse_data(self, data=None):

        if isinstance(data, list):
            for idx, item in enumerate(data):
                data[idx] = self.parse_item(item)
        else:
            data = self.parse_item(data)

        words = str(data).split()
        preview = " ".join(words[:100])
        if len(words) > 100:
            preview += "..."

        logger.info(f"Parsed data: {preview}")
        return data

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

        if requests:
            logger.info(f"Requests: {requests}")

        if responses:
            logger.info(f"Responses: {responses}")

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

    def parse_arguments(self, arguments: list):
        for idx, argument in enumerate(arguments):
            if argument in self.event_outputs:
                argument = self.event_outputs.get(argument, argument)

            try:
                arguments[idx] = ast.literal_eval(argument)
            except Exception as e:
                arguments[idx] = argument

        return arguments

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

    def build_result(self):
        return {
            "url": self.url,
            "status": 0,
            "error": None,
            "progress": "100%",
            "output_filename": self.output_filename,
            "path": self.output_path,
        }

    def execute_events(self):

        ACTIONS = {
            "get": self.get,
            "quit": self.quit,
            "e": self.get_elements,
            "element": self.get_elements,
            "xpath": self.get_elements_by_xpath,
            "name": self.get_elements_by_name,
            "class_name": self.get_elements_by_class_name,
            "id": self.get_elements_by_id,
            "selector": self.get_elements_by_selector,
            "link_text": self.get_elements_by_link_text,
            "partial_link_text": self.get_elements_by_partial_link_text,
            "clear": self.clear_element,
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
            "extract_structured": self.extract_structured,
            "save": self.save,
            "screenshot": self.take_screenshot,
        }

        if not self.events:
            return self.results

        for index, event in enumerate(self.events):

            event = self.parse_event(event)
            variable = event.get("variable")
            action = event.get("action")
            arguments = event.get("arguments")

            if action not in ACTIONS:
                logger.error(f"[Event #{index}] Unknown action: {action}")
                continue

            try:
                arguments = self.parse_arguments(arguments)
                output = ACTIONS[action](*arguments)
                self.event_outputs.update({variable: output})

            except WebDriverException as e:
                logger.error(f"Selenium error: {e}")
                if self.result:
                    self.result["status"] = 1
                    self.result["error"] = (
                        f"[Event #{index}] Failed → {event}\nError: {e}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

                if self.result:
                    self.result["status"] = 1
                    self.result["error"] = (
                        f"[Event #{index}] Failed → {event}\nError: {e}"
                    )

            if self.result:
                self.results.append(self.result)
            self.result = None  # reset result for each event

        return self.results


def get_selenium_options(options_path: str, default_options_path: str = None):

    events = None
    default_options: dict = {}

    if not default_options_path:
        default_options_path = get_option(
            "SELENIUM_PATH", os.path.join(DOWNLOADER_METADATA_DIR, "chrome.json")
        )

    default_options = read_json_file(default_options_path)
    logger.info(f"Using default options from path: {default_options_path}")

    if is_valid_url(options_path):
        events = [f"get({options_path})", "save()", "quit()"]
        events: list
        default_options["events"] = events
    else:
        # combine
        options = read_json_file(options_path)
        default_options.update(options)

    return default_options


def download(
    url_or_path: str,
    default_options_path: str | None = None,
    output_directory: str | None = None,
    proxy: str | None = get_option("PROXY"),
    user_agent: str | None = get_option("USER_AGENT"),
) -> list[dict]:

    results = []

    out_dir = Path(output_directory or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not output_directory:
        output_directory = os.getcwd()

    options = get_selenium_options(url_or_path, default_options_path)

    selenium_downloader = SeleniumDownloader(
        **options,
        url=url_or_path,
        output_directory=output_directory,
        proxy=proxy,
        user_agent=user_agent,
    )

    results = selenium_downloader.execute_events()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Selenium downloader")
    parser.add_argument("url", type=str, help="URL to scrape")
    parser.add_argument(
        "-o",
        "--default_options_path",
        default=get_option(
            "SELENIUM_PATH", os.path.join(DOWNLOADER_METADATA_DIR, "chrome.json")
        ),
        type=str,
    )
    parser.add_argument(
        "-d",
        "--output_directory",
        type=str,
        default=os.getcwd(),
        help="Download directory",
    )
    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=get_option("PROXY"),
        help="Proxy URL (http://, https://, socks5:// etc.)",
    )
    parser.add_argument(
        "-u",
        "--user_agent",
        type=str,
        default=get_option("USER_AGENT"),
        help="Custom User-Agent",
    )
    args = parser.parse_args()

    results = download(
        url_or_path=args.url,
        default_options_path=args.default_options_path,
        output_directory=args.output_directory,
        proxy=args.proxy,
        user_agent=args.user_agent,
    )

    pp.pprint(results)
