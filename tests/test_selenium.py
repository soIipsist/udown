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
options_path = os.path.join(DOWNLOADER_METADATA_DIR, "selenium.json")
options = read_json_file(options_path)
# print(options)
selenium_driver = SeleniumDownloader(**options)


class TestSelenium(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_get_options(self):
        options = get_selenium_options(None)
        print(options)

    def test_download(self):
        download(url, options_path=options_path, output_filename="index.html")

    def test_get_browser_options(self):
        browser_options_metadata = options.get("browser_options")
        browser_options = BrowserOptions(
            selenium_driver.driver_type,
            selenium_driver.browser_type,
            browser_options_metadata,
        ).get_browser_options()

        if options.get("driver_type") == "undetected":
            self.assertTrue(selenium_driver.driver_type == "undetected")
            self.assertTrue(isinstance(browser_options, uc.ChromeOptions))
            print(browser_options)
        else:
            self.assertTrue(selenium_driver.driver_type != "undetected")
            print(browser_options)

    def test_get_driver_instance(self):

        # from selenium.webdriver.support import expected_conditions as EC

        # ec_function = "element_to_be_clickable"
        # print(EC.__dict__.get(ec_function))

        selenium_driver.get_driver_instance()
        self.assertIsNotNone(selenium_driver.driver)

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
        event_dict = selenium_driver.parse_event(event)

        self.assertTrue(event_dict.get("variable") == "var")

        event = f"get({url})"
        event_dict = selenium_driver.parse_event(event)
        print(event_dict)
        self.assertTrue(event_dict.get("variable") == None)


if __name__ == "__main__":
    test_methods = [
        # TestSelenium.test_get_options,
        # TestSelenium.test_download,
        # TestSelenium.test_get_driver_instance,
        # TestSelenium.test_get_browser_options,
        TestSelenium.test_parse_event
    ]
    run_test_methods(test_methods)
