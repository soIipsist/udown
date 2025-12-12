import argparse
from pprint import pp
from src.download import download_command, download_all
from src.downloader import downloader_command, downloader_action


def main():
    parser = argparse.ArgumentParser(prog="udown")
    subparsers = parser.add_subparsers(dest="command")

    # udown download [some_url] -t downloader_type
    # udown downloaders

    download_command(subparsers)
    downloader_command(subparsers)
    args = vars(parser.parse_args())

    command = args.get("command")
    cmd_dict = {"download": download_all, "downloaders": downloader_action}
    action = cmd_dict.get(command)

    if "command" in args:
        args.pop("command")

    output = action(**args)

    if output:
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

# python downloader.py downloads
# python downloader.py "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/ChessSet.jpg/640px-ChessSet.jpg" -d "downloads.txt"
# python downloader.py -d "downloads.txt" -o ~/temp

# python downloader.py -t ytdlp_audio -d "downloads.txt" (type should precede everything unless explicitly defined inside the .txt)
# python downloader.py -t ytdlp_audio -d "downloads.txt" -o ~/temp

# downloaders

# python downloader.py downloaders
# python downloader.py downloaders -t ytdlp_audio
# python downloader.py downloaders add -n ytdlp_2 -t ytdlp_video -d downloader_path.json
