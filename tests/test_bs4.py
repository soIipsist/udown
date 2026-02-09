from pathlib import Path
import os
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from downloaders.bs4 import *


pp = PrettyPrinter(indent=2)


class TestBS4(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_extract(self):
        url = "https://quotes.toscrape.com"
        selector = "a"
        attribute = "href"
        result = extract_selector(url, selector, attribute)
        print(result)


if __name__ == "__main__":
    test_methods = [
        TestBS4.test_extract,
    ]
    run_test_methods(test_methods)
