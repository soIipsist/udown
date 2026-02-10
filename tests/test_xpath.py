from pathlib import Path
import os
from downloaders.xpath import extract_xpath
from test_base import *

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))

from downloaders.selector import *


pp = PrettyPrinter(indent=2)

url = "https://quotes.toscrape.com"


class TestXpath(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_extract_xpath(self):
        xpath = "//a/@href"
        result = extract_xpath(url, xpath=xpath, rules=None, output_filename="extracted2.txt")
        print(result)

if __name__ == "__main__":
    test_methods = [
        TestXpath.test_extract_xpath,
    ]
    run_test_methods(test_methods)
