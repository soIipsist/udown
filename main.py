#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import sys

from src.download import download_command, download_action
from src.downloader import downloader_command, downloader_action, pp
from src.options import options_action, options_command


def main():
    # if "_ARGCOMPLETE" in os.environ:
    #     print("ARGCOMPLETE ACTIVE", file=sys.stderr)
    #     return

    parser = argparse.ArgumentParser(prog="udown")
    subparsers = parser.add_subparsers(dest="command")

    # udown download [some_url] -t downloader_type
    # udown downloaders
    download_parser = download_command(subparsers)
    download_parser.set_defaults(func=download_action)

    downloader_parser = downloader_command(subparsers)
    downloader_parser.set_defaults(func=downloader_action)

    options_parser = options_command(subparsers)
    options_parser.set_defaults(func=options_action)

    import argcomplete

    argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        sys.argv.append("download")
    elif sys.argv[1].startswith("-") or sys.argv[1] not in subparsers.choices:
        sys.argv.insert(1, "download")

    args = parser.parse_args()

    args_dict = vars(args)
    func = args_dict.pop("func", download_action)
    ui = args_dict.get("ui", True)
    command = args_dict.pop("command")

    output = func(**args_dict)

    # print(args_dict)

    if not ui and output:
        pp.pprint(output)


if __name__ == "__main__":
    main()

# tests

# playlist urls
# https://www.youtube.com/playlist?list=PL3A_1s_Z8MQbYIvki-pbcerX8zrF4U8zQ

# regular video urls
# https://youtu.be/MvsAesQ-4zA?si=gDyPQcdb6sTLWipY
# https://youtu.be/OlEqHXRrcpc?si=4JAYOOH2B0A6MBvF

# regular urls (wget)
# https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/ChessSet.jpg/640px-ChessSet.jpg

# downloads

# python download.py downloads
# python download.py "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/ChessSet.jpg/640px-ChessSet.jpg" -d "downloads.txt"
# python download.py "downloads.txt" -o ~/temp

# python download.py -t ytdlp_audio "downloads.txt"
# python download.py -t ytdlp_audio "downloads.txt" -o ~/temp

# downloaders

# python downloader.py downloaders
# python downloader.py downloaders -t ytdlp_audio
# python downloader.py downloaders add -t ytdlp_video -d downloader_path.json
