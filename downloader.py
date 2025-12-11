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
from logger import setup_logger
from sqlite import is_valid_path
from sqlite_item import SQLiteItem, create_connection
from sqlite_conn import create_db, download_values, downloader_values
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


class DownloadStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


logger = setup_logger(name="download", log_dir="/downloads/logs")
logger.disabled = False


class Download(SQLiteItem):
    _downloader = None
    _download_status = DownloadStatus.STARTED
    _start_date = str(datetime.now())
    _end_date = None
    _time_elapsed = None
    _url: str = None
    _download_str: str = None
    _db: sqlite3.Connection = None
    _output_directory: str = None
    _output_filename: str = None
    _output_path: str = None
    _source_url: str = None
    _extra_args: dict = None
    _proxy: str = None

    @property
    def downloader_path(self):
        return getattr(self.downloader, "downloader_path") if self.downloader else None

    def __init__(
        self,
        url: str = None,
        downloader=None,
        download_status: DownloadStatus = DownloadStatus.STARTED,
        start_date: str = None,
        output_directory: Optional[str] = None,
        output_filename: Optional[str] = None,
        proxy: Optional[str] = None,
        extra_args: Optional[str] = None,
    ):
        column_names = [
            "url",
            "downloader",
            "download_status",
            "start_date",
            "end_date",
            "time_elapsed",
            "output_path",
            "source_url",
            "proxy",
            "extra_args",
        ]
        super().__init__(download_values, column_names, db_path=database_path)
        self.url = url
        self.downloader = downloader
        self.download_status = download_status
        self.output_directory = output_directory
        self.output_filename = output_filename
        self.start_date = start_date
        self.proxy = proxy
        self.extra_args = extra_args

        self.table_name = "downloads"
        self.conjunction_type = "OR"
        self.filter_condition = f"url = {self.url}"

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: str):
        self._proxy = proxy

    @property
    def extra_args(self):
        return self._extra_args

    @extra_args.setter
    def extra_args(self, extra_args: str):
        self._extra_args = self.get_extra_args(extra_args)

    def get_extra_args(self, extra_args: str = None):
        args = {}

        if isinstance(extra_args, dict) or not extra_args:
            return extra_args

        parts = re.split(r",(?![^\[]*\])", extra_args)

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                key, value = key.strip(), value.strip()
                try:
                    parsed_value = ast.literal_eval(value)
                except Exception:
                    parsed_value = value
                args[key] = parsed_value
        return args

    @property
    def source_url(self):
        return self._source_url

    @source_url.setter
    def source_url(self, source_url):
        self._source_url = source_url

    @property
    def download_status(self):
        return (
            self._download_status.value
            if isinstance(self._download_status, Enum)
            else self._download_status
        )

    @download_status.setter
    def download_status(self, download_status):
        self._download_status = download_status

    @property
    def output_directory(self):
        if self._output_directory is None:
            return os.getcwd()
        return self._output_directory

    @output_directory.setter
    def output_directory(self, output_directory):
        self._output_directory = output_directory

    @property
    def output_filename(self):
        return self._output_filename

    @output_filename.setter
    def output_filename(self, output_filename: str):
        self._output_filename = output_filename

    @property
    def output_path(self):

        if not self._output_path:
            self._output_path = self.get_output_path()
        return self._output_path

    @output_path.setter
    def output_path(self, output_path: str):
        self._output_path = output_path

    @property
    def start_date(self):
        return self._start_date

    @start_date.setter
    def start_date(self, start_date):
        if start_date is None:
            start_date = str(datetime.now())
        self._start_date = start_date

    @property
    def end_date(self):
        return self._end_date

    @end_date.setter
    def end_date(self, end_date):
        self._end_date = end_date

    @property
    def time_elapsed(self):
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, time_elapsed):
        self._time_elapsed = time_elapsed

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url: str):
        self._url = url

    @property
    def downloader(self):
        if isinstance(self._downloader, str):
            return Downloader(downloader_type=self._downloader).select_first()
        return self._downloader

    @downloader.setter
    def downloader(self, downloader):
        self._downloader = downloader

    def set_download_status_query(
        self, status: DownloadStatus, error_message: str = None
    ):
        self.download_status = status
        logger.info(f"Setting download status: {str(status)}")

        if self.download_status == DownloadStatus.COMPLETED:
            self.end_date = str(datetime.now())
            fmt = "%Y-%m-%d %H:%M:%S.%f"
            start_dt = datetime.strptime(self.start_date, fmt)
            end_dt = datetime.strptime(self.end_date, fmt)

            self.time_elapsed = str(end_dt - start_dt)
            log_message = f"Time elapsed: {self.time_elapsed}"
            logger.info(log_message)
        else:
            data = self.as_dict()
            logger.error(
                f"An unexpected error has occured: {error_message}! \n{pp.pformat(data)} "
            )

        filter_condition = f"url = {self.url} AND downloader = {self.downloader.downloader_type} AND output_path = {self.output_path}"
        self.update(filter_condition)

    def get_output_path(self):
        filename = (
            self.output_filename
            if self.output_filename
            else os.path.basename(urlparse(self.url).path)
        )

        # Decode if bytes (just in case)
        if isinstance(filename, bytes):
            filename = filename.decode("utf-8")

        if isinstance(self.output_directory, bytes):
            output_directory = self.output_directory.decode("utf-8")
        else:
            output_directory = self.output_directory

        return os.path.join(output_directory, filename)

    def __repr__(self):
        return f"{self.downloader}, {self.url}"

    def __str__(self):
        return f"{self.downloader}, {self.url}"

    @classmethod
    def parse_download_string(
        cls,
        url: str,
        downloader_type=None,
        output_directory: str = None,
        output_filename: str = None,
    ):

        url = url.strip()
        parts = url.split(" ") if " " in url else [url]

        # parts = [f'"{arg}"' if " " in arg else arg for arg in parts]

        for part in parts:
            if part.startswith(("http://", "https://")):
                url = part
            elif part.startswith('"') and part.endswith('"'):
                output_filename = part
            elif part.startswith("'") and part.endswith("'"):
                output_filename = part
            else:
                downloader_type = part if part else downloader_type

        if downloader_type is None:
            downloader_type = "ytdlp_video"

        downloader = Downloader(downloader_type).select_first()
        if not downloader:
            raise ValueError(f"Downloader of type '{downloader_type}' does not exist.")

        if output_filename:
            output_filename = output_filename.strip("'").strip('"')

        parsed_info = {
            "URL": url,
            "Downloader": downloader,
            "Output filename": output_filename,
        }

        logger.info(f"Parsed download string {url}:\n{pp.pformat(parsed_info)}")

        return Download(
            url,
            downloader_type,
            output_filename=output_filename,
            output_directory=output_directory,
        )


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

    def get_downloader_args(self, download: Download, func):
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
    def start_downloads(downloads: list[Download]):
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
    return downloader_names


# argparse commands


def downloaders_cmd(
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
            downloaders = d.filter_by(
                ["downloader_type", "downloader_path", "module", "func"]
            )
        else:
            downloaders = d.select_all()

        for downloader in downloaders:
            downloader: Downloader
            pp.pprint(downloader.as_dict(filter_keys))


def download_all_cmd(
    url: str = None,
    downloader_type: str = None,
    output_directory: str = None,
    output_filename: str = None,
    extra_args: str = None,
    **kwargs,
):

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


if __name__ == "__main__":
    # Check if the user skipped the subcommand, and inject 'download'
    if len(sys.argv) == 1 or sys.argv[1] not in [
        "download",
        "downloaders",
        "-h",
        "--help",
    ]:
        sys.argv.insert(1, "download")

    choices = get_downloader_names()
    choices.append("")
    choices.append(None)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    # download cmd
    download_cmd = subparsers.add_parser("download", help="Download a URL")
    download_cmd.add_argument("url", type=str, nargs="?")
    download_cmd.add_argument(
        "-t",
        "--downloader_type",
        default=os.environ.get("DOWNLOADER_TYPE", "ytdlp_video"),
        choices=choices,
        type=str,
    )

    download_cmd.add_argument(
        "-s",
        "--download_status",
        type=DownloadStatus,
        default=None,
    )

    download_cmd.add_argument(
        "-o",
        "--output_directory",
        default=os.environ.get("DOWNLOADS_DIRECTORY"),
        type=str,
    )
    download_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=os.environ.get("DOWNLOAD_KEYS")
    )
    download_cmd.add_argument(
        "-p", "--proxy", default=os.environ.get("DOWNLOAD_PROXY"), type=str
    )
    download_cmd.add_argument("-f", "--output_filename", default=None, type=str)
    download_cmd.add_argument("-e", "--extra_args", default=None, type=str)

    download_cmd.set_defaults(call=download_all_cmd)

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
        default="video_mp4_best",
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

    downloader_cmd.set_defaults(call=downloaders_cmd)
    args = vars(parser.parse_args())
    call = args.get("call")
    args.pop("command")
    args.pop("call")

    output = call(**args)

    if output:
        pp.pprint(output)

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
