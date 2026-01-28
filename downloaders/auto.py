from pprint import PrettyPrinter
from src.downloader import default_downloaders
import argparse

pp = PrettyPrinter(indent=2)


def detect_downloader(**args):
    print(args)
    print(args.get("url"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )

    args = parser.parse_args()

    downloader = detect_downloader()
    results = downloader.download(
        args.urls,
        args.output_directory,
    )

    pp.pprint(results)
