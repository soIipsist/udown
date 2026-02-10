from pathlib import Path
import os
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from downloaders.selector import *


pp = PrettyPrinter(indent=2)

url = "https://quotes.toscrape.com"


class TestSelector(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_extract_selector(self):
        selector = "a"
        attribute = "href"
        result = extract_selector(url, selector, attribute, rules="make_absolute_urls")
        print(result)

if __name__ == "__main__":
    test_methods = [
        TestSelector.test_extract_selector,
    ]
    run_test_methods(test_methods)
