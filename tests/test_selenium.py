from pathlib import Path
import os
from downloaders.selenium_downloader import *
from test_base import *
from src.options import DOWNLOADER_METADATA_DIR

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))


pp = PrettyPrinter(indent=2)

url = "https://quotes.toscrape.com"
url_2 = "https://quotes.toscrape.com/login"
options_path = os.path.join(DOWNLOADER_METADATA_DIR, "firefox.json")
options = read_json_file(options_path)
# print(options)
selenium_downloader = SeleniumDownloader(**options)


class TestSelenium(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_get_selenium_options(self):
        options = get_selenium_options(options_path)
        # print(options)

        path = os.path.join(os.getcwd(), "quotes.json")
        options = get_selenium_options(path, options_path)
        # print(options)

        options = get_selenium_options("https://quotes.toscrape.com")
        print(options)

    def test_get_browser_options(self):
        browser_options_metadata = options.get("browser_options")
        browser_options = BrowserOptions(
            selenium_downloader.browser_type,
            browser_options_metadata,
        ).get_browser_options()

        print(browser_options)

    def test_get_driver_instance(self):

        # from selenium.webdriver.support import expected_conditions as EC

        # ec_function = "element_to_be_clickable"
        # print(EC.__dict__.get(ec_function))

        selenium_downloader.get_driver_instance()
        self.assertIsNotNone(selenium_downloader.driver)

        # cookies = selenium_driver.get_cookies()

        # selenium_driver.add_implicit_wait(10)
        # selenium_driver.get(url)
        # print(cookies)
        # js = "return document.title;"
        # result = selenium_driver.execute_script(js)

        # element = selenium_driver.get_element_by_xpath(
        #     "/html/body/div/div[2]/div[1]/div[1]/div/a[1]"
        # )
        # selenium_driver.click_element(element)

        # selenium_driver.quit()
        # selenium_driver.execute_events()
        # self.assertTrue(isinstance(selenium_driver.driver, webdriver.Chrome))
        # selenium_driver.quit()
        # print("RESULT", result)
        # selenium_driver.execute_events()

    def test_parse_event(self):
        event = f"var = get({url})"
        event_dict = selenium_downloader.parse_event(event)

        self.assertTrue(event_dict.get("variable") == "var")

        # event = f"get({url})"
        # event_dict = selenium_driver.parse_event(event)
        print(event_dict)
        # self.assertTrue(event_dict.get("variable") == None)

    def test_parse_arguments(self):
        events = [f"var = get({url})", "x = get(var)", "x(x)"]

        for idx, event in enumerate(events):

            event_dict = selenium_downloader.parse_event(event)
            variable = event_dict.get("variable")
            arguments = event_dict.get("arguments")

            selenium_downloader.event_outputs.update({variable: arguments})

            print("OLD", arguments)
            # print(variable, arguments)
            new_args = selenium_downloader.parse_arguments(arguments)

            print("NEW", new_args)

    def test_execute_events(self):

        # events = [f"get({url})", "save()", "quit()"]
        # selenium_downloader.events = events
        # results = selenium_downloader.execute_events()

        # self.assertTrue(len(results) == 2)
        # selenium_downloader.get(url)
        # selenium_downloader.save(selenium_downloader.driver.page_source, "index.html")
        # selenium_downloader.quit()

        # events = [
        #     f"get({url})",
        #     "el = e(//span, xpath, True)",
        #     "save(el)",
        #     "quit()",
        # ]
        # selenium_downloader.events = events
        # results = selenium_downloader.execute_events()

        events = [
            f"get({url_2})",
            'username = e(//*[@id="username"], xpath)',
            'password = e(//*[@id="password"], xpath)',
            "button = e(/html/body/div/form/input[2], xpath)",
            "keys(username, hello)",
            "keys(password, world)",
            "save('', output1.html)",
            "click(button)",
            "sleep(10)",
            "delete_cookies(session)",
            "cookies = cookies()",
            "save('', output2.html)",
            "save(cookies, cookies.json)",
            "quit()",
        ]
        selenium_downloader.events = events
        results = selenium_downloader.execute_events()

        print(results)

    def test_download_with_path(self):
        path = os.path.join(os.getcwd(), "secure.json")
        results = download(
            path, default_options_path=options_path, output_directory=None
        )
        print(results)

    def test_download_with_url(self):
        results = download(url, output_directory="/Users/p/Downloads/")
        print(results)

    def test_undetected(self):
        uc.TARGET_VERSION = 78
        version_main = 147

        options = uc.ChromeOptions()

        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(version_main=version_main)
        logger.info(driver.service.path)

        driver.get("https://nowsecure.nl")
        driver.save_screenshot("driver.png")
        options.headless = False

    def test_undetected_with_options(self):
        path = os.path.join(os.getcwd(), "secure.json")
        results = download(
            path, default_options_path=options_path, output_directory=None
        )
        print(results)


if __name__ == "__main__":
    test_methods = [
        # TestSelenium.test_get_selenium_options,
        # TestSelenium.test_get_driver_instance,
        # TestSelenium.test_get_browser_options,
        # TestSelenium.test_parse_event,
        # TestSelenium.test_parse_arguments,
        # TestSelenium.test_has_get_event,
        # TestSelenium.test_execute_events,
        # TestSelenium.test_download_with_url,
        TestSelenium.test_download_with_path,
        # TestSelenium.test_undetected,
        # TestSelenium.test_undetected_with_options
    ]
    run_test_methods(test_methods)
