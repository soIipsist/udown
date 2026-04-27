from enum import Enum
import os
import json
from pathlib import Path
from pprint import PrettyPrinter
import re
import os
import signal
import shutil
import subprocess
import sys
from argparse import ArgumentParser
import tempfile
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote_plus
from downloaders.wget import download as wget_download
from src.settings import DOWNLOADER_METADATA_DIR
from utils import str_to_bool
from utils.logger import setup_logger, write_output
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote, unquote, urlparse, parse_qs, urljoin

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="torrent", log_dir="/udown/torrent")

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

driver = None


class LinkType(str, Enum):
    MAGNET = "magnet"
    INFO = "info"
    TORRENT = "torrent"


class TorrentMode(str, Enum):
    INFO = "info"
    EXTRACT = "extract"
    MAGNET = "magnet"
    TORRENT = "torrent"


class Link:
    _link_type: str = None
    _base_url: str = None
    _tag = None

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, base_url: str):
        self._base_url = base_url

    @property
    def link_type(self):
        return (
            self._link_type.value
            if isinstance(self._link_type, Enum)
            else self._link_type
        )

    @link_type.setter
    def link_type(self, type: str):
        self._link_type = type

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        self._tag = tag

    @property
    def link_str(self):
        return f"{self.get_display_name()} | {self.url}"

    @property
    def url(self):
        return (
            urljoin(self.base_url, self.tag.get("href"))
            if self.base_url
            else self.tag.get("href")
        )

    def get_display_name(self):
        if self.link_type == LinkType.MAGNET.value:
            name = re.search(r"dn=([^&]+)", self.url)
            if name:
                return unquote(name.group(1))

        return self.tag.get_text(strip=True) or self.url

    def to_dict(self):
        return {
            "url": self.url,
            "name": self.get_display_name(),
        }

    def __init__(self, tag, link_type: str, base_url: str = None):
        self.tag = tag
        self.link_type = link_type
        self.base_url = base_url

    @classmethod
    def filter_by_type(cls, links: list, link_type) -> list[Link]:
        return [link for link in links if link.link_type == link_type]

    def __repr__(self):
        return f"{self.url}"

    def __str__(self):
        return f"{self.url}"


def check_fzf(
    links: list[Link] = None,
):
    fzf_path = shutil.which("fzf")

    if fzf_path:
        fzf = subprocess.Popen(
            [fzf_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )

        links_str = "\n".join(link.link_str for link in links)

        stdout, _ = fzf.communicate(links_str)
        selection = stdout.strip()
        return selection if selection else None

    else:
        logger.error("fzf not found!")
        return None


def get_torrent_metadata(torrent_url, use_selenium, metadata):
    page_response = get_page_response(torrent_url, use_selenium)

    soup = BeautifulSoup(page_response, "html.parser")

    container_cfg = metadata.get("details_container", {})
    container = soup.find(
        container_cfg.get("tag"),
        id=container_cfg.get("id"),
        class_=container_cfg.get("class"),
    )

    def get_detail(label):

        if container:
            dt = container.find("dt", string=re.compile(label))
            if dt and dt.find_next_sibling("dd"):
                return dt.find_next_sibling("dd").get_text(strip=True)
        return "N/A"

    fields = metadata.get("fields", {})

    file_size = get_detail(fields.get("Size", {}).get("dt", "Size"))
    seeders = get_detail(fields.get("Seeders", {}).get("dt", "Seeders"))
    leechers = get_detail(fields.get("Leechers", {}).get("dt", "Leechers"))
    type_ = get_detail(fields.get("Type", {}).get("dt", "Type"))

    info_cfg = metadata.get("info", {})
    nfo_div = soup.find(info_cfg.get("tag", "div"), class_=info_cfg.get("class"))
    info = nfo_div.get_text(strip=True) if nfo_div else "No info available"

    metadata_message = f"""
==============================
Torrent Metadata
==============================
Type     : {type_}
Size     : {file_size}
Seeders  : {seeders}
Leechers : {leechers}
------------------------------
Info:
{info}
------------------------------
URL: {torrent_url}
==============================
""".strip()

    logger.info(metadata_message)


def build_search_url(base_url, query):
    q = quote(query)

    if "{query}" in base_url:
        return base_url.replace("{query}", q)

    if "?" in base_url:
        if base_url.endswith("="):
            return f"{base_url}{q}"
        else:
            return f"{base_url}&q={q}"

    if base_url.endswith("/"):
        return f"{base_url}{q}"

    return f"{base_url}/{q}"


def normalize_magnet(magnet: str, normalize: bool = True) -> str:
    magnet = magnet.strip()
    parsed = urlparse(magnet)
    display_name = None

    if parsed.scheme != "magnet":
        return magnet, display_name

    params = parse_qs(parsed.query)

    xt = params.get("xt")
    normalized = f"magnet:?xt={xt[0]}" if normalize else magnet

    dn_list = params.get("dn")
    if dn_list:
        display_name = unquote_plus(dn_list[0])

    logger.info(dn_list)

    return normalized, display_name


def get_output_filename(
    display_name: str, output_directory: str, max_age_seconds: int = 900
):
    expected_name = display_name.strip()
    expected_path = os.path.join(output_directory, expected_name)

    if os.path.exists(expected_path):
        return display_name

    if not os.path.isdir(output_directory):
        return None

    now = time.time()
    best_name = None
    best_mtime = 0.0

    for entry in os.listdir(output_directory):
        if entry.startswith(".") or entry.lower().endswith(
            (".html", ".part", ".torrent")
        ):
            continue

        full_path = os.path.join(output_directory, entry)
        try:
            mtime = os.path.getmtime(full_path)
            if mtime > best_mtime and (now - mtime) <= max_age_seconds:
                best_mtime = mtime
                best_name = entry
        except (OSError, PermissionError):
            continue

    return best_name


def download_torrent(
    torrent: str,
    torrent_directory: str = None,
    confirm_download: bool = True,
    normalize: bool = True,
):
    torrent, display_name = normalize_magnet(torrent, normalize)

    logger.info(f"Torrent: {torrent}")

    result = {
        "url": torrent,
        "status": None,
        "output_filename": display_name,
        "stdout": "",
        "error": None,
    }

    if confirm_download:
        input_str = f"Downloading '{torrent}'. Proceed? (y/n): "
        answer = input(input_str).strip().lower()
        if answer != "y":
            result["status"] = 1
            result["error"] = "Cancelled"
            return [result]

    directory = torrent_directory or os.path.expanduser("~")
    placeholder = "/tmp/transmission-finish-placeholder.sh"

    cmd = [
        "transmission-cli",
        torrent,
        "-w",
        directory,
        "-f",
        placeholder,
        "-g",
        tempfile.mkdtemp(),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=None,
            stderr=None,
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write(f"#!/bin/sh\nkill {proc.pid}\n")
            tmp.flush()
            real_script = tmp.name

        os.chmod(real_script, 0o755)

        os.rename(real_script, placeholder)
        proc.wait()

    except KeyboardInterrupt:
        if "proc" in locals() and proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        logger.warning("Download interrupted by user")
        result["status"] = 1
        result["error"] = "Interrupted by user"

    except Exception as e:
        logger.error(f"Failed to download {torrent}: {e}")
        result["status"] = 1
        result["error"] = str(e)

    finally:

        if not result["error"]:
            result["progress"] = "100%"
            result["output_filename"] = (
                get_output_filename(display_name, directory) if display_name else None
            )
            result["status"] = 0

            logger.info("Download completed successfully")
        try:
            os.unlink(placeholder)
        except OSError:
            pass

    return [result]


def get_page_response(url: str, use_selenium: bool = False):
    try:

        if use_selenium:
            logger.info("Using selenium!")
            global driver
            if not driver:
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                driver = webdriver.Chrome(options=chrome_options)

            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            return driver.page_source
        else:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(e)


def extract_links(page_response, patterns, base_url: str = None):
    info_pattern = patterns.get("info")
    magnet_pattern = patterns.get("magnet")
    torrent_pattern = patterns.get("torrent")

    links = []

    soup = BeautifulSoup(page_response, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if info_pattern and info_pattern in href:
            links.append(Link(tag=tag, link_type=LinkType.INFO, base_url=base_url))

        if magnet_pattern and magnet_pattern in href:
            links.append(Link(tag=tag, link_type=LinkType.MAGNET, base_url=base_url))

        if torrent_pattern and torrent_pattern in href:
            links.append(Link(tag=tag, link_type=LinkType.TORRENT, base_url=base_url))

    return links


def download_torrent_from_url(
    url: str,
    torrent_directory: str = None,
):
    if not os.path.exists(url):
        for result in wget_download(url, torrent_directory, "test.torrent"):
            pass
        url = (
            os.path.join(torrent_directory, "test.torrent")
            if torrent_directory
            else "test.torrent"
        )
    return url


def get_url_from_selection(selection: str):
    parts = selection.split("|")
    url = parts[1] if parts else selection
    return url


def search(
    query: str = None,
    metadata_path: str = None,
    torrent_url: str = None,
    torrent_mode: str = TorrentMode.MAGNET,
    torrent_directory: str = None,
    confirm_download: bool = True,
    normalize: bool = False,
):
    metadata = None
    not_found = False

    if not metadata_path:
        metadata_path = os.path.join(DOWNLOADER_METADATA_DIR, "torrent_default.json")

    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

    if not torrent_url:
        raise ValueError("Base torrent url was not defined!")

    if not torrent_directory:
        torrent_directory = os.getcwd()

    metadata = metadata.get(torrent_url, {})

    if not query:
        query = input("Enter Search Query: ")

    # if it's a magnet or a torrent file, simply download
    if query.startswith("magnet:") or query.endswith(".torrent"):
        results = download_torrent(
            query, torrent_directory, confirm_download, normalize
        )
        return results

    search_url = build_search_url(torrent_url, query)
    logger.info(f"Search url: {search_url}")

    use_selenium = metadata.get("use_selenium", False)
    patterns = metadata.get("patterns", {})
    page_response = get_page_response(search_url, use_selenium)
    links = extract_links(page_response, patterns, search_url)

    if not links:
        logger.info("No results found.")
        return

    info_links = Link.filter_by_type(links, "info")
    magnet_links = Link.filter_by_type(links, "magnet")
    torrent_links = Link.filter_by_type(links, "torrent")

    if torrent_mode == TorrentMode.EXTRACT:
        output = {
            "info_links": [l.to_dict() for l in info_links],
            "magnet_links": [l.to_dict() for l in magnet_links],
            "torrent_links": [l.to_dict() for l in torrent_links],
        }

        path = os.path.join(torrent_directory, "links.json")
        write_output(logger, output, path, append=False)
        return

    # info mode: get metadata
    # magnet mode: get magnet links only
    # torrent mode: get torrent links only

    if torrent_mode == TorrentMode.INFO:
        links = info_links
    elif torrent_mode == TorrentMode.MAGNET:
        links = magnet_links
    else:
        links = torrent_links

    if not links:
        not_found = True
        links = info_links

    selection = check_fzf(links)

    logger.info(f"Using {torrent_mode} MODE for query: {query}.")
    logger.info(f"Selection: {selection}")

    if not selection:
        return

    url = get_url_from_selection(selection)

    if torrent_mode == TorrentMode.INFO:
        get_torrent_metadata(url, use_selenium, metadata)
        return []
    else:
        if not_found:
            logger.info(
                f"{torrent_mode} links not found on search page, checking details page..."
            )
            detail_page = get_page_response(url, use_selenium)
            links = extract_links(detail_page, patterns, url)
            info_links = Link.filter_by_type(links, "info")
            magnet_links = Link.filter_by_type(links, "magnet")
            torrent_links = Link.filter_by_type(links, "torrent")

            if torrent_mode == TorrentMode.INFO:
                torrent_mode = TorrentMode.MAGNET

            if torrent_mode == TorrentMode.MAGNET:
                links = magnet_links
            else:
                links = torrent_links

            url = get_url_from_selection(links[0].link_str) if links else None

        if not url:
            print(f"No {torrent_mode} links found.")
            return

        results = download_torrent(url, torrent_directory, confirm_download, normalize)

    if driver:
        driver.quit()

    return results


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument("-p", "--metadata_path", default=None, type=str)
    parser.add_argument(
        "-u",
        "--torrent_url",
        type=str,
        default=os.environ.get("TORRENT_URL"),
    )
    parser.add_argument(
        "-d",
        "--torrent_directory",
        type=str,
        default=os.environ.get("TORRENT_DIRECTORY"),
    )
    parser.add_argument(
        "-m",
        "--torrent_mode",
        default=os.environ.get("TORRENT_MODE", TorrentMode.MAGNET),
        type=TorrentMode,
    )
    parser.add_argument(
        "-c",
        "--confirm_download",
        default=True,
        type=str_to_bool,
    )
    parser.add_argument("-n", "--normalize", type=str_to_bool, default=True)

    args = parser.parse_args()

    query = args.query
    torrent_url = args.torrent_url
    torrent_mode = args.torrent_mode
    torrent_directory = args.torrent_directory
    metadata_path = args.metadata_path
    confirm_download = args.confirm_download
    normalize = args.normalize
    results = search(
        query,
        metadata_path,
        torrent_url,
        torrent_mode,
        torrent_directory,
        confirm_download,
        normalize,
    )
