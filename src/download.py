import ast
from datetime import datetime
from enum import Enum
import json
import os
import re
import shlex
import sqlite3
from typing import Optional
from urllib.parse import urlparse
from .downloader import (
    Downloader,
    get_downloader_types,
    detect_downloader_type,
    complete_downloader_type,
)
from .options import get_option, str_to_bool
from utils.sqlite_item import SQLiteItem
from utils.sqlite_conn import (
    download_values,
)
from .downloader import database_path, pp, logger


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
    _results = None

    @property
    def results(self):
        return self._results

    @results.setter
    def results(self, results: list):
        self._results = results

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
        self.conjunction_type = "AND"
        self.results = None
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
        self._extra_args = extra_args

    def get_extra_args(self):
        positional = []
        kwargs = {}

        if not self.extra_args:
            return kwargs, positional

        parts = re.split(r",(?![^\[]*\])", self.extra_args)

        for part in parts:
            part = part.strip()

            if "=" in part:
                key, value = part.split("=", 1)
                key, value = key.strip(), value.strip()
                try:
                    parsed_value = ast.literal_eval(value)
                except Exception:
                    parsed_value = value
                kwargs.update({key: parsed_value})
            else:
                try:
                    parsed_value = ast.literal_eval(part)
                except Exception:
                    parsed_value = part
                positional.append(parsed_value)

        return kwargs, positional

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
        if self._downloader_type == "auto" or not self._downloader_type:
            self._downloader_type = detect_downloader_type(self._url)

        if isinstance(self._downloader_type, str):
            return Downloader(downloader_type=self._downloader_type).select_first()

    @downloader.setter
    def downloader(self, downloader):
        self._downloader = downloader

    def set_progress_query(self, progress: str, filter_condition: str):
        self.progress = progress
        logger.info(f"Progress: {str(progress)}")
        self.update(filter_condition)

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

        filter_condition = f"url = {self.url} AND downloader_type = {self.downloader_type} AND output_path = {self.output_path}"
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

    def insert(self):
        if not self.downloader_type:
            self.downloader_type = "ytdlp_video"
        return super().insert()

    @classmethod
    def parse_download_string(
        cls,
        **args,
    ):
        downloads = []
        url = args.get("url")
        base_downloader_type = args.get("downloader_type")
        base_output_directory = args.get("output_directory")
        base_output_filename = args.get("output_filename")

        logger.info(f"Parsing download string: url={url}, args={args}")

        def parse_line(line: str):
            url = None
            downloader_type = base_downloader_type
            output_filename = base_output_filename

            parts = shlex.split(line)

            for part in parts:
                if part.startswith(("http://", "https://", "magnet:")):
                    url = part
                    continue

                if Downloader(part).select_first() or part == "auto":
                    downloader_type = part
                    continue

                output_filename = part

            if downloader_type == "auto":
                downloader_type = detect_downloader_type(url)

            downloader = Downloader(downloader_type).select_first()
            if not downloader:
                raise ValueError(
                    f"Downloader of type '{downloader_type}' does not exist."
                )

            return Download(
                url,
                downloader_type,
                output_filename=output_filename,
                output_directory=base_output_directory,
            )

        if os.path.exists(url) and not url.endswith(".torrent"):
            with open(url, "r") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    downloads.append(parse_line(line))
        else:
            downloads.append(Download(**args))

        return downloads

    def download(self, downloader: Downloader = None):
        if not downloader:
            if not self._downloader_type:
                self._downloader_type = detect_downloader_type(self._url)

            downloader = Downloader(
                downloader_type=self._downloader_type
            ).select_first()

        results = downloader.start_downloads([self])
        self.results = results
        return results


def download_action(**args):
    action = args.pop("action", get_option("DOWNLOAD_ACTION", "list"))
    url = args.get("url") or None
    ui = args.pop("ui", True)
    filter_keys = args.pop("filter_keys", get_option("DOWNLOAD_KEYS", None))
    conjunction_type = args.pop("conjunction_type", get_option("DOWNLOAD_OP", "AND"))

    if action is None:
        action = "download" if url else "list"

    if url:
        downloads = Download.parse_download_string(**args)
    else:
        downloads = [Download(**args)]

    if action in {"add", "insert"}:
        for d in downloads:
            if not d.url:
                raise ValueError("No URL provided.")
            d.insert()

    elif action == "download":
        for d in downloads:
            if not d.url:
                raise ValueError("No URL provided.")
            d.download()

    elif action == "delete":
        for d in downloads:
            filter_condition = (
                f"url = {d.url} AND downloader_type = {d.downloader_type}"
            )
            result = d.delete(filter_condition)

            if result:
                logger.info(f"Download successfully deleted: {d.url}")

    else:
        if filter_keys:
            filter_keys = filter_keys.split(",")
        args.pop("url", None)

        d = Download(**args)
        d.conjunction_type = conjunction_type
        downloads = d.filter_by(filter_keys)

        if ui:
            from .tui_main import UDownApp

            downloader_types = get_downloader_types()
            UDownApp(
                downloads,
                action=download_action,
                args=args,
                downloader_types=downloader_types,
            ).run()

    return downloads


def download_command(subparsers):

    download_cmd = subparsers.add_parser("download", help="Download a URL")
    download_cmd.add_argument("url", type=str, nargs="?")
    download_cmd.add_argument(
        "-a",
        "--action",
        default=get_option("DOWNLOAD_ACTION", None),
        choices=["download", "add", "insert", "delete", "list"],
    )
    type_arg = download_cmd.add_argument(
        "-t",
        "--downloader_type",
        default=get_option("DOWNLOADER_TYPE", None),
        type=str,
    )
    type_arg.completer = complete_downloader_type

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
    download_cmd.add_argument(
        "-ui", "--ui", default=get_option("USE_TUI", True), type=str_to_bool
    )
    download_cmd.add_argument(
        "-c",
        "--conjunction_type",
        default=get_option("DOWNLOAD_OP", "AND"),
        type=str,
        choices=["AND", "OR"],
    )

    return download_cmd
