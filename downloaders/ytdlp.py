import yt_dlp
import argparse
import os
import json
from pprint import PrettyPrinter
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

bool_choices = ["0", "1", 0, 1, "true", "false", True, False, None]
parent_directory = os.path.dirname(os.path.abspath(__file__))
pp = PrettyPrinter(indent=2)


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
        print(e)


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
        outtmpl = f"{output_filename}.%(ext)s"

    if prefix:
        outtmpl = f"{prefix}{outtmpl}"

    if not output_directory:
        if ytdlp_format == "ytdlp_audio":
            output_directory = os.environ.get("YTDLP_AUDIO_DIRECTORY")

        elif ytdlp_format == "ytdlp_video":
            output_directory = os.environ.get("YTDLP_VIDEO_DIRECTORY")

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
    update_options: bool = False,
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

    if not options_path and not update_options:
        options_file = (
            "audio_options.json"
            if ytdlp_format == "ytdlp_audio"
            else "video_options.json"
        )
        script_directory = os.path.dirname(__file__)
        options_path = os.path.join(script_directory, options_file)

    if os.path.exists(options_path):  # read from metadata file, if it exists
        print(f"Using ytdlp options from path: {options_path}.")
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

    if not update_options:
        return options

    options: dict

    if ytdlp_format == "ytdlp_video":  # default ytdlp_video options
        options.update(
            {
                "progress": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
            }
        )

        if not extension:
            extension = "mp4"

    elif ytdlp_format == "ytdlp_audio":
        if not extension:
            extension = "mp3"

        options.update(
            {
                "progress": True,
                "ignoreerrors": True,
            }
        )

    video_format = get_video_format(options, ytdlp_format, custom_format)
    postprocessors = get_postprocessors(options, ytdlp_format, extension)
    options_postprocessor_args = get_postprocessor_args(options, postprocessor_args)

    options["merge_output_format"] = extension
    options["postprocessors"] = postprocessors
    options["postprocessor_args"] = options_postprocessor_args
    options["format"] = video_format

    return options


def get_entry_url(original_url: str, entry: dict, is_playlist: bool) -> str:

    url = entry.get("webpage_url")

    if not is_playlist:
        return original_url

    if url:
        return url

    id = entry.get("id")
    if not id:
        return None
    parsed = urlparse(original_url)
    hostname = parsed.hostname or ""

    if "youtube" in hostname or "youtu.be" in hostname:
        url = f"https://www.youtube.com/watch?v={id}"
    else:
        new_path = parsed.path.rstrip("/") + "/" + id
        url = urlunparse(parsed._replace(path=new_path))

    print(f"Entry url found from ID {id}: {url}.")
    return url


def get_entry_filename(entry: dict):
    title = entry.get("title")

    if not title:
        return None

    ext = entry.get("ext", "mp4")
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
        print(e)

    return results


def get_channel_info(channel_id_or_url: str):
    url = (
        f"https://www.youtube.com/{channel_id_or_url}/videos"
        if not channel_id_or_url.startswith("https")
        else channel_id_or_url
    )
    results = extract_ytdlp_info(url)
    return results


def download(
    urls: list,
    options_path="",
    ytdlp_format: str = "ytdlp_video",
    custom_format: str = None,
    update_options: bool = False,
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
    print("Downloading with yt-dlp...")
    options = get_options(
        options_path,
        ytdlp_format,
        custom_format,
        update_options,
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

    pp.pprint(options)

    for url in urls:
        print(f"\nProcessing URL: {url}")
        try:
            with yt_dlp.YoutubeDL(options) as ytdl:
                info = ytdl.extract_info(url, download=False)

                # Determine if it's a playlist or a single video
                is_playlist = info.get("entries") is not None
                entries = info.get("entries") if is_playlist else [info]

                if is_playlist:
                    print(
                        f"Playlist: {info.get('title', 'Untitled')} ({len(entries)} videos)"
                    )

                for idx, entry in enumerate(entries):
                    entry_url = None

                    result = {
                        "original_url": url,
                        "entry_index": idx,
                        "is_playlist": is_playlist,
                        "entry_url": entry_url,
                        "status": 1,
                    }

                    if not entry:
                        print(f"Skipping unavailable video at index {idx}.")
                        result["error"] = "Unavailable entry"
                        yield result
                        continue

                    entry_url = get_entry_url(url, entry, is_playlist)
                    entry_filename = get_entry_filename(entry)

                    if not entry_url:
                        print(f"Missing URL at index {idx}. Skipping.")
                        result["error"] = "Missing entry URL"
                        yield result
                        continue

                    result["entry_url"] = entry_url
                    result["entry_filename"] = entry_filename
                    print(f"Downloading: {entry.get('title', entry_url)}")
                    status = ytdl.download([entry_url])

                    result.update(
                        {
                            "status": status,
                            "entry": entry,
                        }
                    )

                    if status != 0:
                        result["error"] = "Download failed"

                    yield result

        except KeyboardInterrupt as e:
            print("User interrupted the download.")
            result = {
                "original_url": url,
                "status": 1,
                "error": str(e),
                "is_playlist": is_playlist,
            }
            yield result

        except yt_dlp.utils.DownloadError as e:
            print(f"Download error: {e}")
            result = {
                "original_url": url,
                "status": 1,
                "error": str(e),
                "is_playlist": is_playlist,
            }
            yield result

        except SystemExit as e:
            print(f"SystemExit: {e} — continuing...")
            result = {
                "original_url": url,
                "status": 1,
                "error": f"SystemExit: {e}",
                "is_playlist": is_playlist,
            }
            yield result

        except Exception as e:
            print(f"Unexpected error: {e}")
            result = {
                "original_url": url,
                "status": 1,
                "error": f"Unexpected error: {e}",
                "is_playlist": is_playlist,
            }
            yield result


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("-r", "--removed_args", default=None, nargs="+")
    parser.add_argument(
        "-f",
        "--ytdlp_format",
        default=os.environ.get("YTDLP_FORMAT", "ytdlp_video"),
        choices=["ytdlp_video", "ytdlp_audio"],
    )
    parser.add_argument(
        "-d",
        "--output_directory",
        type=str,
        default=os.environ.get("YTDLP_OUTPUT_DIRECTORY"),
    )
    parser.add_argument(
        "-p", "--prefix", default=os.environ.get("YTDLP_PREFIX"), type=str
    )
    parser.add_argument("-e", "--extension", default=None)
    parser.add_argument("-cf", "--custom_format", default=None)
    parser.add_argument("-ppa", "--postprocessor_args", default=None, nargs="+")
    parser.add_argument(
        "-o", "--options_path", default=os.environ.get("YTDLP_OPTIONS_PATH", "")
    )
    parser.add_argument(
        "-u",
        "--update_options",
        default=os.environ.get("YTDLP_UPDATE_OPTIONS", False),
        type=str_to_bool,
        choices=bool_choices,
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
            args.update_options,
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
        pp.pprint(result)

# playlist tests
# python ytdlp.py "https://youtube.com/playlist?list=OLAK5uy_nTBnmorryZikTJrjY0Lj1lHG_DWy4IPvk" -f ytdlp_audio
# python ytdlp.py "https://music.youtube.com/watch?v=owZyZrWppGg&list=PLcSQ3bJVgbvb43FGbe7c550xI7gZ9NmBW"

# ytdlp_video only tests
# python ytdlp.py "https://www.youtube.com/watch?v=RlXjyYlM4xo"
# python ytdlp.py "https://www.youtube.com/watch?v=RlXjyYlM4xo" "https://music.youtube.com/watch?v=n3WmS_Yj0jU&si=gC3_A3MrL0RYhooO"

# ytdlp_audio only tests
# python ytdlp.py "https://www.youtube.com/watch?v=RlXjyYlM4xo" "https://music.youtube.com/watch?v=n3WmS_Yj0jU&si=gC3_A3MrL0RYhooO" -f ytdlp_audio
# python ytdlp.py "https://www.youtube.com/watch?v=RlXjyYlM4xo" -f ytdlp_audio -i 0
