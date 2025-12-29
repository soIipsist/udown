import argparse
import ast
from datetime import datetime
from enum import Enum
import os
import re
import sqlite3
from typing import Optional
from urllib.parse import urlparse
from venv import logger
from src.downloader import (
    Downloader,
    get_downloader_names,
)
from src.options import get_option
from src.tui_downloads import UDownApp
from utils.sqlite_item import SQLiteItem
from utils.sqlite_conn import (
    download_values,
)
from src.downloader import database_path, pp


class DownloadStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class Download(SQLiteItem):
    _downloader: Downloader = None
    _downloader_type: str = None
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
    _progress: str = "0"

    @property
    def downloader_path(self):
        return getattr(self.downloader, "downloader_path") if self.downloader else None

    def __init__(
        self,
        url: str = None,
        downloader_type=None,
        download_status: DownloadStatus = DownloadStatus.STARTED,
        start_date: str = None,
        end_date: str = None,
        time_elapsed: str = None,
        output_directory: Optional[str] = None,
        output_filename: Optional[str] = None,
        output_path: Optional[str] = None,
        source_url: Optional[str] = None,
        proxy: Optional[str] = None,
        extra_args: Optional[str] = None,
        progress: Optional[str] = None,
    ):
        column_names = [
            "url",
            "downloader_type",
            "download_status",
            "start_date",
            "end_date",
            "time_elapsed",
            "output_directory",
            "output_filename",
            "output_path",
            "source_url",
            "proxy",
            "extra_args",
            "progress",
        ]
        super().__init__(download_values, column_names, db_path=database_path)
        self.url = url
        self.downloader_type = downloader_type
        self.download_status = download_status
        self.start_date = start_date
        self.end_date = end_date
        self.time_elapsed = time_elapsed
        self.output_directory = output_directory
        self.output_filename = output_filename
        self.output_path = output_path
        self.source_url = source_url
        self.proxy = proxy
        self.extra_args = extra_args
        self.progress = progress
        self.table_name = "downloads"
        self.conjunction_type = "OR"
        self.filter_condition = f"url = {self.url}"

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, progress: str):
        self._progress = progress

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
            return os.path.join(self._output_directory, self._output_filename)
        return self._output_path

    @output_path.setter
    def output_path(self, output_path: str):
        self._output_path = self.get_output_path(output_path)

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
    def downloader_type(self):
        return self._downloader_type

    @downloader_type.setter
    def downloader_type(self, downloader_type: str):
        self._downloader_type = downloader_type

    @property
    def downloader(self):
        if isinstance(self._downloader_type, str):
            return Downloader(downloader_type=self._downloader_type).select_first()

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

        filter_condition = f"url = {self.url} AND downloader_type = {self.downloader.downloader_type} AND output_path = {self.output_path}"
        self.update(filter_condition)

    def get_output_path(self, output_path: str | bytes = None):
        def to_str(val):
            if isinstance(val, bytes):
                return val.decode("utf-8", errors="replace")
            return val

        if output_path:
            return to_str(output_path)

        filename = self._output_filename
        if not filename:
            parsed = urlparse(to_str(self.url))
            filename = os.path.basename(parsed.path)

        filename = to_str(filename)

        output_directory = self._output_directory
        if not output_directory:
            output_directory = os.getcwd()

        output_directory = to_str(output_directory)

        return os.path.join(output_directory, filename)

    def __repr__(self):
        return f"{self.downloader_type}, {self.url}"

    def __str__(self):
        return f"{self.downloader_type}, {self.url}"

    def insert(self):
        if not self.downloader_type:
            self.downloader_type = "ytdlp_video"
        return super().insert()

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

    def download(self, downloader: Downloader = None):
        if not downloader:
            downloader = self.downloader

        if not downloader:
            raise ValueError("No downloader available for this download.")

        results = downloader.start_downloads([self])
        return results


def download_action(**args):

    downloads = []
    url = args.get("url")
    filter_keys = args.get("filter_keys")

    if "filter_keys" in args:
        args.pop("filter_keys")

    if url:
        download = Download.parse_download_string(**args)
        if download is not None:
            downloads.append(download)
    else:
        if filter_keys:
            filter_keys = filter_keys.split(",")

        d = Download(**args)
        downloads = d.filter_by(filter_keys)

    return downloads


def download_command(subparsers):
    choices = get_downloader_names()

    download_cmd = subparsers.add_parser("download", help="Download a URL")
    download_cmd.add_argument("url", type=str, nargs="?")
    download_cmd.add_argument(
        "-t",
        "--downloader_type",
        default=get_option("DOWNLOADER_TYPE", ""),
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
        default=get_option("DOWNLOAD_DIRECTORY"),
        type=str,
    )
    download_cmd.add_argument("-f", "--output_filename", default=None, type=str)
    download_cmd.add_argument("-op", "--output_path", default=None, type=str)
    download_cmd.add_argument("-sd", "--start_date", default=None, type=str)
    download_cmd.add_argument("-ed", "--end_date", default=None, type=str)
    download_cmd.add_argument("-te", "--time_elapsed", default=None, type=str)

    download_cmd.add_argument(
        "-k", "--filter_keys", type=str, default=get_option("DOWNLOAD_KEYS")
    )
    download_cmd.add_argument(
        "-p", "--proxy", default=get_option("DOWNLOAD_PROXY"), type=str
    )
    download_cmd.add_argument("-e", "--extra_args", default=None, type=str)
    download_cmd.add_argument("-pr", "--progress", default=None, type=str)

    return download_cmd
