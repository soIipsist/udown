import ast
from collections.abc import Iterable
from importlib import import_module
import os
from pprint import PrettyPrinter
import re
import sqlite3
from datetime import datetime
from enum import Enum
import sys
from typing import List, Optional
from urllib.parse import urlparse
from utils.logger import setup_logger
from utils.sqlite import is_valid_path
from utils.sqlite_item import SQLiteItem, create_connection
from utils.sqlite_conn import create_db, download_values, downloader_values
import argparse
import inspect

script_directory = os.path.dirname(__file__)
downloaders_directory = os.path.join(script_directory, "downloaders")

pp = PrettyPrinter(indent=2)

database_path = os.environ.get(
    "DOWNLOADS_DB_PATH", os.path.join(script_directory, "downloads.db")
)

# environment variables
# DOWNLOADER="ytdlp"
# DOWNLOADS_FILENAME="$HOME/videos/downloads.txt"
# DOWNLOADS_DB_PATH="$HOME/scripts/downloads.db"
# DOWNLOADS_DIRECTORY="$HOME/videos"
# YTDLP_FORMAT="ytdlp_audio"
# YTDLP_OPTIONS_PATH="$HOME/scripts/video_options.json"
# FFMPEG_OPTS="-protocol_whitelist file,http,https,tcp,tls"
# YTDLP_UPDATE_OPTIONS="1"
# YTDLP_VIDEO_DIRECTORY="$HOME/mnt/"
# YTDLP_AUDIO_DIRECTORY="$HOME/mnt/ssd/Music"
# VENV_PATH="$HOME/venv"

# create connection and tables
db_exists = os.path.exists(database_path)
db = create_connection(database_path)
create_db(database_path)


logger = setup_logger(name="download", log_dir="/downloads/logs")
logger.disabled = False


class Downloader(SQLiteItem):

    _downloader_type: str = None
    _downloader_path: str = None
    _downloader_args: list = None
    _func = None
    _module = None

    @property
    def module(self):
        return self._module

    @module.setter
    def module(self, module: str):
        self._module = module

    @property
    def func(self):
        return self._func

    @func.setter
    def func(self, func: str):
        self._func = func

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
        self._downloader_type = downloader_type or None

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
        func: str = None,
        downloader_args: str = None,
    ):
        column_names = [
            "downloader_type",
            "downloader_path",
            "module",
            "func",
            "downloader_args",
        ]

        super().__init__(downloader_values, column_names, db_path=database_path)
        self.downloader_type = downloader_type
        self.downloader_path = downloader_path
        self.module = module
        self.func = func
        self.downloader_args = downloader_args
        self.conjunction_type = "OR"
        self.filter_condition = f"downloader_type = {self._downloader_type}"
        self.table_name = "downloaders"

    def __repr__(self):
        return f"{self.downloader_type}"

    def __str__(self):
        return f"{self.downloader_type}"

    def get_function(self):
        # determine what function to run for each download
        module = import_module(self.module)
        func = getattr(module, self.func)
        return func

    def get_downloader_args(self, download, func):
        """Passes all Download values to the appropriate download func."""

        func_signature = inspect.signature(func)
        func_params = func_signature.parameters

        args_dict = {}

        if not self.downloader_args:
            for name, param in func_params.items():
                if param.default is not inspect.Parameter.empty:
                    args_dict[name] = param.default
                else:
                    args_dict[name] = getattr(download, name, None)
            return args_dict

        keys = [key.strip() for key in self.downloader_args.split(",")]
        func_keys = {
            k.strip(): v.strip()
            for k, v in (key.split("=", 1) for key in keys if "=" in key)
        }

        for idx, param in enumerate(func_params):
            key = None
            if idx < len(keys):
                key = keys[idx]

            if key and "=" not in key:
                args_val = getattr(download, key, key)
                args_dict[param] = args_val
            else:
                if param in func_keys:
                    val = func_keys[param]
                    args_val = getattr(download, val, val)

                    if args_val and args_val.lower() == "false":
                        args_val = False
                    elif args_val and args_val.lower() == "true":
                        args_val = True
                    args_dict[param] = args_val

            extra_args = download.extra_args

            if extra_args and param in extra_args:
                logger.info(f"Extra arguments: \n{extra_args}")
                args_dict[param] = extra_args.get(param)

        return args_dict

    @staticmethod
    def start_downloads(downloads):
        from src.download import Download, DownloadStatus

        download_results = []

        for idx, download in enumerate(downloads):
            if download.output_directory:
                os.makedirs(download.output_directory, exist_ok=True)

            logger.info(f"Starting {download.downloader} download.")
            downloader = download.downloader
            downloader: Downloader

            try:
                if not downloader:
                    raise ValueError(f"Downloader not found at index {idx}!")

                func = downloader.get_function()
                downloader_args = downloader.get_downloader_args(download, func)
                logger.info(f"Downloader args: \n{downloader_args}")

                result_iter = func(**downloader_args)

                if isinstance(result_iter, (str, dict)):
                    result_iter = [result_iter]
                elif isinstance(result_iter, Iterable):
                    pass
                else:
                    result_iter = [result_iter]

                for result in result_iter:
                    entry_url = result.get("entry_url", download.url)
                    status_code = result.get("status", 1)
                    error_message = result.get("error")
                    entry_filename = result.get("entry_filename")

                    if entry_filename:
                        download.output_filename = entry_filename

                    child_download = Download(
                        entry_url,
                        download.downloader,
                        output_directory=download.output_directory,
                        output_filename=download.output_filename,
                    )

                    child_download.insert()

                    if status_code == 1:
                        child_download.set_download_status_query(
                            DownloadStatus.INTERRUPTED, error_message
                        )
                    else:
                        child_download.set_download_status_query(
                            DownloadStatus.COMPLETED, error_message
                        )

                    download_results.append(result)

            except Exception as e:
                print("Exception: ", e)
                continue

        return download_results


default_downloaders = [
    Downloader(
        "ytdlp",
        None,
        "ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video",
        os.path.join(downloaders_directory, "video_mp4_best.json"),
        "ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_subs",
        os.path.join(downloaders_directory, "video_mp4_subs.json"),
        "ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_avc1",
        os.path.join(downloaders_directory, "video_avc1.json"),
        "ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_audio",
        os.path.join(downloaders_directory, "audio_mp3_best.json"),
        "ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "wget",
        None,
        "wget",
        "download",
        "url, output_directory",
    ),
    Downloader(
        "urllib", None, "url_lib", "download", "url, output_directory, output_filename"
    ),
    Downloader(
        "ytdlp_channel",
        None,
        "ytdlp_channel",
        "download",
        "url",
    ),
]

if not db_exists:
    Downloader.insert_all(default_downloaders)
    print("Successfully generated default downloaders.")


def get_downloader_names():
    downloader_names = [
        downloader.downloader_type for downloader in Downloader().select_all()
    ]
    downloader_names.append("")
    downloader_names.append(None)
    return downloader_names


def download_all(
    url: str = None,
    downloader_type: str = None,
    output_directory: str = None,
    output_filename: str = None,
    extra_args: str = None,
    **kwargs,
):
    from src.download import Download

    downloads = []

    if not url:
        download_status = kwargs.get("download_status")
        download = Download(
            downloader=downloader_type,
            download_status=download_status,
            extra_args=extra_args,
        )
        downloads = download.filter_by()

        logger.info(f"Fetching downloads from file {database_path}.")
        print(f"Total downloads ({len(downloads)}):")

        for d in downloads:
            filter_keys = kwargs.get("filter_keys")
            pp.pprint(d.as_dict(filter_keys))
        downloads = []
    else:
        download = Download.parse_download_string(
            url, downloader_type, output_directory, output_filename
        )
        if download is not None:
            download.proxy = kwargs.get("proxy")
            download.extra_args = extra_args
            downloads.append(download)

    Downloader.start_downloads(downloads)


def downloader_action(
    action: str,
    downloader_type: str = None,
    downloader_path: str = None,
    module: str = None,
    func: str = None,
    downloader_args: str = None,
    filter_keys: str = None,
):
    d = Downloader(downloader_type, downloader_path, module, func, downloader_args)
    downloaders = [d]

    if action == "add":
        if d.module is None:
            d.module = "ytdlp"
        if d.func is None:
            d.func = "download"
        d.upsert()
    elif action == "delete":
        d.delete()
    elif action == "reset":
        Downloader.insert_all(default_downloaders)
        print("Successfully generated default downloaders.")
    else:  # list downloaders

        logger.info(f"Fetching downloaders from file {database_path}.")

        if downloader_type:
            print("yo", downloader_type)

            downloaders = d.filter_by(
                ["downloader_type", "downloader_path", "module", "func"]
            )
        else:
            downloaders = d.select_all()

        for downloader in downloaders:
            downloader: Downloader
            pp.pprint(downloader.as_dict(filter_keys))


def downloader_command(subparsers):
    choices = get_downloader_names()

    # downloader cmd
    downloader_cmd = subparsers.add_parser("downloaders", help="List downloaders")
    downloader_cmd.add_argument(
        "action",
        type=str,
        choices=["add", "delete", "list", "reset"],
        default="list",
        nargs="?",
    )
    downloader_cmd.add_argument(
        "-t",
        "--downloader_type",
        type=str,
        default="",
        choices=choices,
    )
    downloader_cmd.add_argument(
        "-d", "--downloader_path", type=is_valid_path, default=None
    )
    downloader_cmd.add_argument("-f", "--func", type=str, default=None)
    downloader_cmd.add_argument("-m", "--module", type=str, default=None)
    downloader_cmd.add_argument("-a", "--downloader_args", type=str, default=None)
    downloader_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=os.environ.get("DOWNLOADER_KEYS")
    )
