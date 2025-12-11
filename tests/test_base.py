import unittest
import os
import subprocess

parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parent_directory)

from pprint import PrettyPrinter


class TestBase(unittest.TestCase):

    def setUp(self) -> None:
        self.logging = True
        self.extension = "json"
        self.pp = PrettyPrinter(indent=3)

    def execute_cmd(self, cmd):
        os.chdir(f"{parent_directory}/src")
        print(cmd)
        completed_process = subprocess.run(cmd, shell=True)
        exit_code = completed_process.returncode
        self.assertEqual(exit_code, 0)

    def log_data(self, *args, **kwargs):
        if self.logging:
            for d in args:
                print(d)

    def get_files_directory(self):
        return f"{parent_directory}/tests/files"

    def get_file(self, file: str):
        return os.path.join(self.get_files_directory(), file)

    @classmethod
    def generate_default_test_methods(self):
        methods = [
            method_name.replace("test_", "")
            for method_name in dir(self)
            if callable(getattr(self, method_name)) and method_name.startswith("test")
        ]
        return methods


def run_test_methods(test_methods: list):

    if callable(test_methods):
        test_methods = [test_methods]

    default_tests = []
    for test_method in test_methods:
        name = test_method.__name__
        class_name = test_method.__qualname__.split(".")[0]

        default_test = f"{class_name}.{name}"
        default_tests.append(default_test)

    unittest.main(defaultTest=default_tests)


if __name__ == "__main__":
    unittest.main()
