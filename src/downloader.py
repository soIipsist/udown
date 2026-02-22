from collections.abc import Iterable
from importlib import import_module
import json
import os
from pprint import PrettyPrinter
from .options import (
    get_option,
    PROJECT_DIR,
    DOWNLOADER_METADATA_DIR,
    str_to_bool,
    ALLOWED_MODULES,
)
from utils.logger import setup_logger
from utils.sqlite import is_valid_path
from utils.sqlite_item import SQLiteItem, create_connection
from utils.sqlite_conn import create_db, downloader_values
import inspect


pp = PrettyPrinter(indent=2)
database_path = get_option("DATABASE_PATH", os.path.join(PROJECT_DIR, "downloads.db"))

# create connection and tables
db_exists = os.path.exists(database_path)
db = create_connection(database_path)
create_db(database_path)


logger = setup_logger(name="downloader", log_dir="/udown/downloader")
logger.disabled = False


def detect_downloader_type(url: str) -> str:
    url = url.strip()

    if url.startswith("magnet:") or url.endswith(".torrent"):
        downloader_type = "transmission"

    elif "music.youtube" in url:
        downloader_type = "ytdlp_audio"

    elif "youtube.com" in url or "youtu.be" in url:
        downloader_type = "ytdlp_video"

    else:
        downloader_type = "wget"

    logger.info(f"Downloader detected for url '{url}': {downloader_type}.")

    return downloader_type


class Downloader(SQLiteItem):

    _downloader_type: str = None
    _downloader_path: str = None
    _downloader_args: list = None
    _downloader_func = None
    _module = None

    @property
    def module(self):
        return self._module

    @module.setter
    def module(self, module: str):
        self._module = module

    @property
    def downloader_func(self):
        return self._downloader_func

    @downloader_func.setter
    def downloader_func(self, downloader_func: str):
        self._downloader_func = downloader_func

    @property
    def downloader_args(self):
        return self._downloader_args

    @downloader_args.setter
    def downloader_args(self, downloader_args: str):
        self._downloader_args = downloader_args

    @property
    def downloader_type(self):
        return self._downloader_type

    @downloader_type.setter
    def downloader_type(self, downloader_type):
        self._downloader_type = downloader_type

    @property
    def downloader_path(self):
        return self._downloader_path

    @downloader_path.setter
    def downloader_path(self, downloader_path):
        self._downloader_path = (
            os.path.abspath(downloader_path.strip()) if downloader_path else ""
        )

    def __init__(
        self,
        downloader_type: str = None,
        downloader_path: str = None,
        module: str = None,
        downloader_func: str = None,
        downloader_args: str = None,
    ):
        column_names = [
            "downloader_type",
            "downloader_path",
            "module",
            "downloader_func",
            "downloader_args",
        ]

        super().__init__(downloader_values, column_names, db_path=database_path)
        self.downloader_type = downloader_type
        self.downloader_path = downloader_path
        self.module = module
        self.downloader_func = downloader_func
        self.downloader_args = downloader_args
        self.table_name = "downloaders"
        self.conjunction_type = "OR"
        self.filter_condition = f"downloader_type = {self.downloader_type}"

    def __repr__(self):
        return json.dumps(
            self.as_dict(),
            indent=1,
            ensure_ascii=False,
        )

    def __str__(self):
        return json.dumps(
            self.as_dict(),
            indent=1,
            ensure_ascii=False,
        )

    @classmethod
    def reset_all(cls, items: list):
        cls.upsert_all(items)
        logger.info("Successfully generated default downloaders.")

    def get_function(self):
        module_name = self.module.strip()
        func_name = self.downloader_func.strip()

        if module_name not in ALLOWED_MODULES:
            logger.warning(
                "Using custom module: %s\n"
                "This can execute arbitrary code. Proceed only if you trust it.",
                module_name,
            )
            response = (
                input("Proceed with this custom downloader? [y/N]: ").strip().lower()
            )
            if response not in ("y", "yes"):
                logger.info("User cancelled loading custom module.")
                raise ValueError("Loading of custom module cancelled by user")

            logger.info("User confirmed proceeding with custom module.")

        try:
            module = import_module(module_name)
            func = getattr(module, func_name)
            if not callable(func):
                raise ValueError(
                    f"'{func_name}' is not callable in module '{module_name}'"
                )
            return func

        except ImportError as e:
            raise ValueError(f"Failed to import module '{module_name}': {e}")
        except AttributeError:
            raise ValueError(
                f"Function '{func_name}' not found in module '{module_name}'"
            )
        except Exception as e:
            raise ValueError(
                f"Unexpected error loading '{module_name}.{func_name}': {e}"
            )

    def get_downloader_args(self, download, func):
        """Passes all Download values to the appropriate download func."""

        func_signature = inspect.signature(func)
        func_params = list(func_signature.parameters.values())

        args_dict = {}

        if not self.downloader_args:
            for param in func_params:
                if param.default is not inspect.Parameter.empty:
                    args_dict[param.name] = param.default
                else:
                    args_dict[param.name] = getattr(download, param.name, None)
            return args_dict

        keys = [key.strip() for key in self.downloader_args.split(",")]
        func_keys = {
            k.strip(): v.strip()
            for k, v in (key.split("=", 1) for key in keys if "=" in key)
        }

        extra_kwargs, extra_positionals = download.get_extra_args()

        if extra_kwargs:
            logger.info(f"Extra kwargs:\n{extra_kwargs}")
        if extra_positionals:
            logger.info(f"Extra positional args:\n{extra_positionals}")

        pos_iter = iter(extra_positionals)

        for idx, param in enumerate(func_params):
            if param.name in extra_kwargs:
                args_dict[param.name] = extra_kwargs[param.name]
                continue

            key = keys[idx] if idx < len(keys) else None

            if key and "=" not in key:
                args_dict[param.name] = getattr(download, key, key)
                continue

            if param.name in func_keys:
                val = func_keys[param.name]
                args_val = getattr(download, val, val)

                if isinstance(args_val, str):
                    if args_val.lower() == "false":
                        args_val = False
                    elif args_val.lower() == "true":
                        args_val = True

                args_dict[param.name] = args_val
                continue

            try:
                args_dict[param.name] = next(pos_iter)
                continue
            except StopIteration:
                pass

            if param.default is not inspect.Parameter.empty:
                args_dict[param.name] = param.default
            else:
                args_dict[param.name] = getattr(download, param.name, None)

        return args_dict

    @staticmethod
    def start_downloads(downloads):
        from src.download import Download, DownloadStatus

        download_results = []

        for idx, download in enumerate(downloads):
            if download.output_directory:
                os.makedirs(download.output_directory, exist_ok=True)

            logger.info(f"Starting {download.downloader_type} download.")
            downloader = download.downloader
            downloader: Downloader
            is_playlist = False

            try:
                if not downloader:
                    raise ValueError(f"Downloader not found at index {idx}!")
                func = downloader.get_function()
                downloader_args = downloader.get_downloader_args(download, func)
                logger.info(f"Downloader args: \n{downloader_args}")

                result_iter = func(**downloader_args)

                if result_iter is None:
                    download_results.append({})
                    continue
                if isinstance(result_iter, (str, dict)):
                    result_iter = [result_iter]
                elif isinstance(result_iter, Iterable):
                    pass
                else:
                    result_iter = [result_iter]

                is_playlist = False

                for result in result_iter:
                    source_url = None
                    if not isinstance(result, dict):
                        result = {"url": download.url, "stdout": result, "status": 0}

                    url = result.get("url", download.url)
                    status_code = result.get("status", 1)
                    error_message = result.get("error")
                    source_url = result.get("source_url")
                    progress = result.get("progress")

                    downloader_type = download.downloader_type
                    output_directory = download.output_directory
                    output_filename = result.get(
                        "output_filename", download.output_filename
                    )

                    if result.get("is_playlist") is True:
                        is_playlist = True
                        source_url = source_url

                    child_download = Download(
                        url,
                        downloader_type,
                        output_directory=output_directory,
                        output_filename=output_filename,
                        source_url=source_url,
                    )

                    filter_condition = (
                        f"url = {child_download.url} AND "
                        f"downloader_type = {child_download.downloader_type} AND "
                        f"output_path = {child_download.output_path}"
                    )

                    # logger.info(filter_condition)

                    if progress is not None:
                        child_download.progress = progress
                        child_download.set_progress_query(progress, filter_condition)

                    child_download.upsert(filter_condition)

                    if status_code == 1 or error_message is not None:
                        child_download.set_download_status_query(
                            DownloadStatus.INTERRUPTED, error_message
                        )
                    elif status_code == 0:
                        child_download.set_download_status_query(
                            DownloadStatus.COMPLETED, error_message
                        )

                    download_results.append(result)

            except Exception as e:
                print("Exception: ", e)
                continue

        if is_playlist:
            download.set_download_status_query(DownloadStatus.COMPLETED)

        return download_results


default_downloaders = [
    Downloader(
        "ytdlp",
        None,
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video",
        os.path.join(DOWNLOADER_METADATA_DIR, "video_mp4_best.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_subs",
        os.path.join(DOWNLOADER_METADATA_DIR, "video_mp4_subs.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_avc1",
        os.path.join(DOWNLOADER_METADATA_DIR, "video_avc1.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_audio",
        os.path.join(DOWNLOADER_METADATA_DIR, "audio_mp3_best.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "wget",
        None,
        "downloaders.wget",
        "download",
        "url, output_directory, output_filename",
    ),
    Downloader(
        "urllib",
        None,
        "downloaders.url_lib",
        "download",
        "url, output_directory, output_filename",
    ),
    Downloader(
        "ytdlp_channel",
        None,
        "downloaders.ytdlp_channel",
        "download",
        "url",
    ),
    Downloader(
        "transmission",
        None,
        "downloaders.transmission",
        "download",
        "url, output_directory",
    ),
    Downloader(
        "selector",
        None,
        "downloaders.selector",
        "extract_selector",
        "url, selector=a, attribute=href, output_directory=output_directory, output_filename=output_filename, rules=make_absolute_urls",
    ),
    Downloader(
        "xpath",
        None,
        "downloaders.xpath",
        "extract_xpath",
        "url, xpath=//a/@href, output_directory=output_directory, output_filename=output_filename, rules=make_absolute_urls",
    ),
    Downloader(
        "selenium",
        os.path.join(DOWNLOADER_METADATA_DIR, "selenium.json"),
        "downloaders.selenium_downloader",
        "download",
        "url, downloader_path, output_directory, output_filename",
    ),
]

if not db_exists:
    Downloader.reset_all(default_downloaders)


def get_downloader_types():
    downloader_types = [
        downloader.downloader_type for downloader in Downloader().select_all()
    ]
    downloader_types.append("")
    downloader_types.append(None)
    return downloader_types


def list_downloaders(d, downloader_type):
    logger.info(f"Fetching downloaders from file {database_path}.")

    if downloader_type:

        downloaders = d.filter_by(
            ["downloader_type", "downloader_path", "module", "downloader_func"]
        )
    else:
        downloaders = d.select_all()

    return downloaders


def downloader_action(
    **args,
):
    action = args.pop("action", get_option("DOWNLOAD_ACTION", "list"))
    ui = args.pop("ui", True)
    filter_keys = args.pop("filter_keys", get_option("DOWNLOADER_KEYS", None))
    conjunction_type = args.pop("conjunction_type", get_option("DOWNLOADER_OP", "AND"))

    downloaders = []
    d = Downloader(**args)
    d.conjunction_type = conjunction_type

    if action == "add" or action == "insert":
        if not d.module:
            d.module = "downloaders.ytdlp"
        if not d.downloader_func:
            d.downloader_func = "download"
        d.upsert()
    elif action == "delete":
        result = d.delete()
        if result:
            print(f"Downloader {d.downloader_type} was successfully deleted.")
    elif action == "reset":
        Downloader.reset_all(default_downloaders)
    else:
        filter_keys = filter_keys.split(",") if filter_keys else None
        downloaders = d.filter_by(filter_keys)
        if ui:
            from .tui_main import UDownApp

            downloader_types = get_downloader_types()
            UDownApp(
                downloaders,
                "downloaders",
                downloader_action,
                args,
                downloader_types,
            ).run()
    return downloaders


def complete_downloader_type(prefix, parsed_args, **kwargs):
    return [t for t in get_downloader_types() if t and t.startswith(prefix)]


def downloader_command(subparsers):
    downloader_cmd = subparsers.add_parser("downloaders", help="List downloaders")
    downloader_cmd.add_argument(
        "action",
        type=str,
        choices=["add", "insert", "delete", "list", "reset"],
        default=get_option("DOWNLOADER_ACTION", None),
        nargs="?",
    )

    type_arg = downloader_cmd.add_argument("-t", "--downloader_type", type=str)
    type_arg.completer = complete_downloader_type

    downloader_cmd.add_argument(
        "-d", "--downloader_path", type=is_valid_path, default=None
    )
    downloader_cmd.add_argument("-f", "--downloader_func", type=str, default=None)
    downloader_cmd.add_argument("-m", "--module", type=str, default=None)
    downloader_cmd.add_argument("-args", "--downloader_args", type=str, default=None)
    downloader_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=get_option("DOWNLOADER_KEYS")
    )
    downloader_cmd.add_argument(
        "-ui", "--ui", default=get_option("USE_TUI", True), type=str_to_bool
    )
    downloader_cmd.add_argument(
        "-c",
        "--conjunction_type",
        default=get_option("DOWNLOADER_OP", "AND"),
        type=str,
        choices=["AND", "OR"],
    )

    return downloader_cmd
