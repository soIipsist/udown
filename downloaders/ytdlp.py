import threading
import yt_dlp
import argparse
import os
import json
from pprint import PrettyPrinter
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from queue import Empty, Queue
from src.options import get_option
from utils.logger import setup_logger

bool_choices = ["0", "1", 0, 1, "true", "false", True, False, None]
parent_directory = os.path.dirname(os.path.abspath(__file__))
pp = PrettyPrinter(indent=2)

logger = setup_logger(name="ytdlp", log_dir="/udown/ytdlp")


def get_urls(urls: list, removed_args: list = None):
    if isinstance(urls, str):
        urls = [urls]

    if not removed_args:
        return urls

    remove_set = set(removed_args)
    return [
        urlunparse(
            parsed._replace(
                query=urlencode(
                    [(k, v) for k, v in parse_qsl(parsed.query) if k not in remove_set]
                )
            )
        )
        for url in urls
        if (parsed := urlparse(url))
    ]


def str_to_bool(string: str):
    return string in ["1", "true", True]


def read_json_file(json_file, errors=None):
    try:
        with open(json_file, "r", errors=errors) as file:
            json_object = json.load(file)
            return json_object
    except Exception as e:
        logger.error(str(e))


def get_outtmpl(
    options: dict,
    ytdlp_format: str,
    prefix: str = None,
    output_directory: str = None,
    output_filename: str = None,
):

    outtmpl = options.get("outtmpl")

    if outtmpl is not None:
        return outtmpl

    outtmpl = f"%(title)s.%(ext)s"

    if output_filename:
        base, _ = os.path.splitext(output_filename)
        base = base or output_filename
        outtmpl = f"{base}.%(ext)s"

    if prefix:
        outtmpl = f"{prefix}{outtmpl}"

    if not output_directory:
        if ytdlp_format == "ytdlp_audio":
            output_directory = get_option("YTDLP_AUDIO_DIRECTORY")

        elif ytdlp_format == "ytdlp_video":
            output_directory = get_option("YTDLP_VIDEO_DIRECTORY")

    if output_directory:
        outtmpl = f"{output_directory}/{outtmpl}"

    return outtmpl


def get_video_format(options: dict, ytdlp_format: str, custom_format: str = None):
    video_format = options.get("format")

    if custom_format:
        return custom_format

    if not video_format:
        if ytdlp_format == "ytdlp_audio":
            video_format = "bestaudio/best"
        else:
            video_format = "bestvideo+bestaudio"

    return video_format


def get_ytdlp_format(ytdlp_format: str = "ytdlp_video"):

    if ytdlp_format and ytdlp_format.endswith(".txt"):
        ytdlp_format = os.path.basename(ytdlp_format).removesuffix(".txt")

    valid_formats = ["ytdlp_audio", "ytdlp_video"]

    file_formats = {
        "music": "ytdlp_audio",
        "mp3": "ytdlp_audio",
        "videos": "ytdlp_video",
    }

    ytdlp_format = file_formats.get(ytdlp_format, ytdlp_format)

    return ytdlp_format if ytdlp_format in valid_formats else "ytdlp_video"


def get_postprocessors(options: dict, ytdlp_format: str, extension: str):
    postprocessors: list = options.get("postprocessors", [])

    embed_subtitle = {"already_have_subtitle": False, "key": "FFmpegEmbedSubtitle"}
    extract_audio = {"key": "FFmpegExtractAudio", "preferredcodec": extension}

    if ytdlp_format == "ytdlp_video":
        if embed_subtitle not in postprocessors:
            postprocessors.append(embed_subtitle)
    else:
        if extract_audio not in postprocessors:
            postprocessors.append(extract_audio)

    return postprocessors


def get_postprocessor_args(options: dict, postprocessor_args: list = []):
    if not postprocessor_args:
        postprocessor_args = []

    options_postprocessor_args: list = options.get("postprocessor_args", [])
    options_postprocessor_args.extend(postprocessor_args)
    return options_postprocessor_args


def get_options(
    options_path="",
    ytdlp_format: str = "ytdlp_video",
    custom_format: str = None,
    prefix: str = None,
    extension: str = None,
    postprocessor_args: list = None,
    output_directory=None,
    output_filename=None,
    sleep_interval: str = None,
    max_sleep_interval: str = None,
    proxy: str = None,
):

    ytdlp_format = get_ytdlp_format(ytdlp_format)

    if os.path.exists(options_path):  # read from metadata file, if it exists
        logger.info(f"Using ytdlp options from path: {options_path}.")
        options = read_json_file(options_path)
    else:
        options = {}

    outtmpl = get_outtmpl(
        options, ytdlp_format, prefix, output_directory, output_filename
    )
    options["outtmpl"] = outtmpl

    if proxy:
        options["proxy"] = proxy

    if sleep_interval:
        options["sleep_interval"] = sleep_interval

    if max_sleep_interval:
        options["max_sleep_interval"] = max_sleep_interval

    if ytdlp_format == "ytdlp_video":  # default ytdlp_video options

        if not extension:
            extension = "mp4"

    elif ytdlp_format == "ytdlp_audio":
        if not extension:
            extension = "mp3"

    video_format = get_video_format(options, ytdlp_format, custom_format)
    postprocessors = get_postprocessors(options, ytdlp_format, extension)
    options_postprocessor_args = get_postprocessor_args(options, postprocessor_args)

    options["postprocessors"] = postprocessors
    options["postprocessor_args"] = options_postprocessor_args
    options["format"] = video_format

    return options


def get_entry_url(source_url: str, entry: dict, is_playlist: bool) -> str:

    url = entry.get("webpage_url")

    if not is_playlist:
        return source_url

    if url:
        return url

    id = entry.get("id")
    if not id:
        return None
    parsed = urlparse(source_url)
    hostname = parsed.hostname or ""

    if "youtube" in hostname or "youtu.be" in hostname:
        url = f"https://www.youtube.com/watch?v={id}"
    else:
        new_path = parsed.path.rstrip("/") + "/" + id
        url = urlunparse(parsed._replace(path=new_path))

    logger.info(f"Entry url found from ID {id}: {url}.")
    return url


def get_entry_filename(entry: dict, uses_ffmpeg: bool = False):
    title = entry.get("title")

    if not title:
        return None

    ext = entry.get("ext", "mp4")

    downloads = entry.get("requested_downloads")

    if downloads and uses_ffmpeg:
        filepath = downloads[0].get("filepath")
        if filepath:
            new_ext = os.path.splitext(filepath)[1].lstrip(".")
            if new_ext != ext:
                ext = new_ext

    filename = f"{title}.{ext}"

    return filename


def extract_ytdlp_info(url: str):
    options = {
        "extract_flat": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ytdl:
            results = ytdl.extract_info(url, download=False)
    except Exception as e:
        logger.error(str(e))

    return results


def get_channel_info(channel_id_or_url: str):
    url = (
        f"https://www.youtube.com/{channel_id_or_url}/videos"
        if not channel_id_or_url.startswith("https")
        else channel_id_or_url
    )
    results = extract_ytdlp_info(url)
    return results


def check_ffmpeg(options: dict) -> bool:
    for pp in options.get("postprocessors", []):
        key = pp.get("key", "")
        if key.startswith("FFmpegExtractAudio"):
            return True
    return False


class YTDLPProgressState:
    def __init__(self):
        self.progress = "0.0%"
        self.speed = None
        self.eta = None
        self.status = None
        self.done = False
        self.error = None

    def hook(self, d):
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes")

            if total and downloaded:
                percent = (downloaded / total) * 100
                self.progress = f"{percent:.1f}%"
            else:
                self.progress = d.get("_percent_str", self.progress)

            self.speed = d.get("_speed_str") or d.get("speed")
            self.eta = d.get("_eta_str") or d.get("eta")

        elif status == "finished":
            self.progress = "100%"
            self.status = 0
            self.done = True

        elif status in ("error", "aborted"):
            self.status = 1
            self.error = d.get("error", "Download failed")
            self.done = True


def download(
    urls: list,
    options_path="",
    ytdlp_format: str = "ytdlp_video",
    custom_format: str = None,
    prefix: str = None,
    extension: str = None,
    postprocessor_args: list = None,
    removed_args: list = None,
    output_directory=None,
    output_filename=None,
    sleep_interval: str = None,
    max_sleep_interval: str = None,
    proxy: str = None,
):
    logger.info("Downloading with yt-dlp...")
    options = get_options(
        options_path,
        ytdlp_format,
        custom_format,
        prefix,
        extension,
        postprocessor_args,
        output_directory,
        output_filename,
        sleep_interval,
        max_sleep_interval,
        proxy,
    )

    urls = get_urls(urls, removed_args)
    logger.info(pp.pformat(options))

    for url in urls:
        logger.info(f"\nProcessing URL: {url}")
        progress_state = YTDLPProgressState()
        options["progress_hooks"] = [progress_state.hook]
        options["remote_components"] = ["ejs:github"]
        result = {"url": url}

        try:
            with yt_dlp.YoutubeDL(options) as ytdl:
                info = ytdl.extract_info(url, download=True)

                # Determine if it's a playlist or a single video
                is_playlist = info.get("entries") is not None
                entries = info.get("entries") if is_playlist else [info]
                uses_ffmpeg = check_ffmpeg(options)

                if is_playlist:
                    logger.info(
                        f"Playlist: {info.get('title', 'Untitled')} ({len(entries)} videos)"
                    )

                for idx, entry in enumerate(entries):
                    entry_url = None

                    result = {
                        "url": url,
                        "index": idx,
                        "is_playlist": is_playlist,
                        "progress": progress_state.progress,
                        "status": None,
                    }

                    if not entry:
                        error = f"Skipping unavailable video at index {idx}."
                        logger.error(error)
                        result["error"] = error
                        return result

                    entry_url = get_entry_url(url, entry, is_playlist)
                    entry_filename = get_entry_filename(entry, uses_ffmpeg)

                    if not entry_url:
                        error = f"Missing URL at index {idx}. Skipping."
                        logger.error(error)
                        result["error"] = error
                        return result

                    result["url"] = entry_url
                    result["output_filename"] = entry_filename
                    logger.info(f"Filename: {entry_filename}")
                    logger.info(f"Downloading: {entry.get('title', entry_url)}")
                    logger.info(f"Progress: {progress_state.progress}")
                    result["status"] = 0

                    return result

        except KeyboardInterrupt as e:
            logger.error("User interrupted the download.")
            result = {
                "url": result.get("url") or url,
                "status": 1,
                "error": str(e),
                "is_playlist": is_playlist,
            }
            return result

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download error: {e}")
            result = {
                "url": result.get("url") or url,
                "status": 1,
                "error": str(e),
                "is_playlist": is_playlist,
            }
            return result

        except SystemExit as e:
            logger.error(f"SystemExit: {e} — continuing...")
            result = {
                "url": result.get("url") or url,
                "status": 1,
                "error": f"SystemExit: {e}",
                "is_playlist": is_playlist,
                "progress": progress_state.progress,
            }
            return result

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            result = {
                "url": result.get("url") or url,
                "status": 1,
                "error": f"Unexpected error: {e}",
                "is_playlist": is_playlist,
                "progress": progress_state.progress,
            }
            return result


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("-r", "--removed_args", default=None, nargs="+")
    parser.add_argument(
        "-f",
        "--ytdlp_format",
        default=get_option("YTDLP_FORMAT", "ytdlp_video"),
        choices=["ytdlp_video", "ytdlp_audio"],
    )
    parser.add_argument(
        "-d",
        "--output_directory",
        type=str,
        default=get_option("YTDLP_OUTPUT_DIRECTORY"),
    )
    parser.add_argument("-p", "--prefix", default=get_option("YTDLP_PREFIX"), type=str)
    parser.add_argument("-e", "--extension", default=None)
    parser.add_argument("-cf", "--custom_format", default=None)
    parser.add_argument("-ppa", "--postprocessor_args", default=None, nargs="+")
    parser.add_argument(
        "-o", "--options_path", default=get_option("YTDLP_OPTIONS_PATH", "")
    )

    parser.add_argument("-P", "--proxy", default=None)
    parser.add_argument("-F", "--output_filename", default=None)
    parser.add_argument("-si", "--sleep_interval", default=None)
    parser.add_argument("-msi", "--max_sleep_interval", default=None)

    args = parser.parse_args()
    results = list(
        download(
            args.urls,
            args.options_path,
            args.ytdlp_format,
            args.custom_format,
            args.prefix,
            args.extension,
            args.postprocessor_args,
            args.removed_args,
            args.output_directory,
            args.output_filename,
            args.sleep_interval,
            args.max_sleep_interval,
            args.proxy,
        )
    )

    for result in results:
        if result.get("entry"):
            result.pop("entry")
        logger.info(result)
