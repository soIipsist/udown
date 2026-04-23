#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import sys

from src.download import download_command, download_action, complete_downloader_type
from src.downloader import downloader_command, downloader_action, pp
from src.update import update_command, update_action
from src.options import options_action, options_command, get_option
from utils import parse_date, str_to_bool


def get_defaults(parser, args):
    defaults = {}

    for action in parser._actions:
        if action.dest != argparse.SUPPRESS:
            defaults[action.dest] = action.default

    subparsers_action = next(
        (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)),
        None,
    )

    if subparsers_action and args.command in subparsers_action.choices:
        subparser = subparsers_action.choices[args.command]

        for action in subparser._actions:
            if action.dest != argparse.SUPPRESS:
                defaults[action.dest] = action.default

    return defaults


def get_extra_args(args_dict: dict, unknown_args):
    return args_dict


def main():
    # if "_ARGCOMPLETE" in os.environ:
    #     print("ARGCOMPLETE ACTIVE", file=sys.stderr)
    #     return

    parser = argparse.ArgumentParser(prog="udown")

    type_arg = parser.add_argument(
        "-t",
        "--downloader_type",
        default=get_option("DOWNLOADER_TYPE", None),
        type=str,
    )

    parser.add_argument("-f", "--output_filename", default=None, type=str)
    parser.add_argument("-op", "--output_path", default=None, type=str)
    parser.add_argument("-sd", "--start_date", default=None, type=parse_date)
    parser.add_argument("-ed", "--end_date", default=None, type=parse_date)
    parser.add_argument("-te", "--time_elapsed", default=None, type=str)
    parser.add_argument(
        "-ui", "--ui", default=get_option("USE_TUI", True), type=str_to_bool
    )
    type_arg.completer = complete_downloader_type

    subparsers = parser.add_subparsers(dest="command")

    download_parser = download_command(subparsers)
    download_parser.set_defaults(func=download_action)

    downloader_parser = downloader_command(subparsers)
    downloader_parser.set_defaults(func=downloader_action)

    options_parser = options_command(subparsers)
    options_parser.set_defaults(func=options_action)

    update_parser = update_command(subparsers)
    update_parser.set_defaults(func=update_action)

    import argcomplete

    argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        sys.argv.append("download")
    elif sys.argv[1].startswith("-") or sys.argv[1] not in subparsers.choices:
        sys.argv.insert(1, "download")

    args, unknown = parser.parse_known_args()
    args._defaults = get_defaults(parser, args)
    args_dict = vars(args)

    func = args_dict.pop("func", download_action)
    ui = args_dict.get("ui", True)
    command = args_dict.pop("command")

    print(args_dict)
    print(unknown)

    if args_dict.get("extra_args"):
        args_dict["extra_args"] = get_extra_args()

    output = func(**args_dict)

    if not ui and output:
        pp.pprint(output)


if __name__ == "__main__":
    main()
