import argparse
from downloader import download_cmd


def main():
    parser = argparse.ArgumentParser(prog="downloader")
    subparsers = parser.add_subparsers(dest="command")

    # download.register(subparsers)
    # upload.register(subparsers)
    # listing.register(subparsers)

    args = parser.parse_args()
    args.func(args)
