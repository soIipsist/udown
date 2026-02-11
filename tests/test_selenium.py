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


class TestSelenium(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_get_options(self):
        options = get_selenium_options(options_path)
        print(options)


if __name__ == "__main__":
    test_methods = [
        TestSelenium.test_get_options,
    ]
    run_test_methods(test_methods)
