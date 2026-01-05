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
from src.options import get_option, PROJECT_PATH, DOWNLOADER_DIRECTORY, str_to_bool
from utils.logger import setup_logger
from utils.sqlite import is_valid_path
from utils.sqlite_item import SQLiteItem, create_connection
from utils.sqlite_conn import create_db, download_values, downloader_values
import argparse
import inspect


pp = PrettyPrinter(indent=2)

database_path = get_option("DATABASE_PATH", os.path.join(PROJECT_PATH, "downloads.db"))

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
        self.table_name = "downloaders"
        self.conjunction_type = "OR"
        self.filter_condition = f"downloader_type = {self.downloader_type}"

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

            # logger.info(f"Starting {download.downloader} download.")
            downloader = download.downloader
            downloader: Downloader
            is_playlist = False

            try:
                if not downloader:
                    raise ValueError(f"Downloader not found at index {idx}!")
                func = downloader.get_function()
                downloader_args = downloader.get_downloader_args(download, func)
                # logger.info(f"Downloader args: \n{downloader_args}")

                result_iter = func(**downloader_args)

                if isinstance(result_iter, (str, dict)):
                    result_iter = [result_iter]
                elif isinstance(result_iter, Iterable):
                    pass
                else:
                    result_iter = [result_iter]

                is_playlist = False

                for result in result_iter:
                    source_url = None
                    url = result.get("url", download.url)
                    status_code = result.get("status", 1)
                    error_message = result.get("error")
                    source_url = result.get("source_url")
                    progress = result.get("progress")

                    downloader_type = download.downloader_type
                    output_directory = download.output_directory
                    output_filename = (
                        download.output_filename
                        if download.output_filename
                        else result.get("output_filename")
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

                    if progress is not None:
                        child_download.progress = progress
                        child_download.set_progress_query(progress, filter_condition)

                    child_download.upsert(filter_condition)

                    if status_code == 1 or error_message is not None:
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
        os.path.join(DOWNLOADER_DIRECTORY, "video_mp4_best.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_subs",
        os.path.join(DOWNLOADER_DIRECTORY, "video_mp4_subs.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_video_avc1",
        os.path.join(DOWNLOADER_DIRECTORY, "video_avc1.json"),
        "downloaders.ytdlp",
        "download",
        "url, downloader_path, output_directory=output_directory, output_filename=output_filename, proxy=proxy",
    ),
    Downloader(
        "ytdlp_audio",
        os.path.join(DOWNLOADER_DIRECTORY, "audio_mp3_best.json"),
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


def list_downloaders(d, downloader_type):
    logger.info(f"Fetching downloaders from file {database_path}.")

    if downloader_type:

        downloaders = d.filter_by(
            ["downloader_type", "downloader_path", "module", "func"]
        )
    else:
        downloaders = d.select_all()

    return downloaders


def downloader_action(
    **args,
):
    action = args.pop("action", "list")
    filter_keys = args.pop("filter_keys", None)
    ui = args.pop("ui", True)
    conjunction_type = args.pop("conjunction_type", "AND")

    downloaders = []
    d = Downloader(**args)
    d.conjunction_type = conjunction_type

    if action == "add" or action == "insert":
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
    else:
        filter_keys = filter_keys.split(",") if filter_keys else None
        downloaders = d.filter_by(filter_keys)
        if ui:
            from src.tui_downloads import UDownApp

            UDownApp(downloaders, "downloaders", downloader_action, args).run()
    return downloaders


def downloader_command(subparsers):
    choices = get_downloader_names()

    # downloader cmd
    downloader_cmd = subparsers.add_parser("downloaders", help="List downloaders")
    downloader_cmd.add_argument(
        "-a",
        "--action",
        type=str,
        choices=["add", "insert", "delete", "list", "reset"],
        default="list",
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
    downloader_cmd.add_argument("-args", "--downloader_args", type=str, default=None)
    downloader_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=get_option("DOWNLOADER_KEYS")
    )
    downloader_cmd.add_argument(
        "-ui", "--ui", default=get_option("USE_TUI", True), type=str_to_bool
    )
    downloader_cmd.add_argument(
        "-c", "--conjunction_type", default="AND", type=str, choices=["AND", "OR"]
    )

    return downloader_cmd
