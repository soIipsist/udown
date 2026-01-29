from utils.sqlite import is_valid_path
from utils.sqlite_item import SQLiteItem
from utils.sqlite_conn import extractor_values
from .downloader import database_path
from .options import get_option, str_to_bool


class Extractor(SQLiteItem):
    def __init__(self, column_names=None, logging=False, db_path=None):
        super().__init__(extractor_values, column_names, db_path=database_path)


def extractor_command(subparsers):
    # extractor cmd
    extractor_cmd = subparsers.add_parser("extractors", help="List extractors")
    extractor_cmd.add_argument(
        "action",
        type=str,
        choices=["add", "insert", "delete", "list", "reset"],
        default=get_option("EXTRACTOR_ACTION", None),
        nargs="?",
    )
    extractor_cmd.add_argument("-t", "--extractor_type", type=str, default="")
    # type_arg.completer = complete_extractor_type
    extractor_cmd.add_argument(
        "-p", "--extractor_path", type=is_valid_path, default=None
    )
    extractor_cmd.add_argument("-f", "--func", type=str, default=None)
    extractor_cmd.add_argument("-m", "--module", type=str, default=None)
    extractor_cmd.add_argument("-args", "--extractor_args", type=str, default=None)
    extractor_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=get_option("EXTRACTOR_KEYS")
    )
    extractor_cmd.add_argument(
        "-ui", "--ui", default=get_option("USE_TUI", True), type=str_to_bool
    )
    extractor_cmd.add_argument(
        "-c",
        "--conjunction_type",
        default=get_option("EXTRACTOR_OP", "AND"),
        type=str,
        choices=["AND", "OR"],
    )

    return extractor_cmd
