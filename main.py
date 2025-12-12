import argparse
from downloader import download_cmd


def main():
    parser = argparse.ArgumentParser(prog="udown")
    subparsers = parser.add_subparsers(dest="command")

    # udown download [some_url] -t downloader_type
    # udown downloaders
    args = parser.parse_args()
    args.func(args)
