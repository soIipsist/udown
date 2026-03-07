import os
import json
from pathlib import Path
from pprint import PrettyPrinter
import re
import shutil
import subprocess
from urllib.parse import quote
from argparse import ArgumentParser
import requests
from bs4 import BeautifulSoup

from downloaders.ytdlp import str_to_bool
from utils.logger import setup_logger

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="torrent", log_dir="/udown/torrent")


def check_fzf(links):
    fzf_path = shutil.which("fzf")

    if fzf_path:
        fzf = subprocess.Popen(
            [fzf_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )

        stdout, _ = fzf.communicate("\n".join(links))
        selection = stdout.strip()
        return selection if selection else None

    else:
        output_file = Path("torrent_results.txt")

        with open(output_file, "w") as f:
            f.write("\n".join(links))

        logger.error(f"fzf not found. Results exported to: {output_file}")
        return None


def get_torrent_metadata(torrent_url, metadata_path=None):
    response = requests.get(torrent_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    config = None

    if metadata_path and os.path.exists(metadata_path):
        with open(metadata_path) as f:
            config = json.load(f)

    if config:

        container_cfg = config.get("details_container")
        container = soup.find(
            container_cfg.get("tag"),
            id=container_cfg.get("id"),
            class_=container_cfg.get("class"),
        )

        def get_detail(label):
            dt = container.find("dt", string=re.compile(label))
            if dt and dt.find_next_sibling("dd"):
                return dt.find_next_sibling("dd").get_text(strip=True)
            return "N/A"

        fields = config.get("fields", {})

        file_size = get_detail(fields.get("Size", "Size"))
        seeders = get_detail(fields.get("Seeders", "Seeders"))
        leechers = get_detail(fields.get("Leechers", "Leechers"))
        type_ = get_detail(fields.get("Type", "Type"))

        info_cfg = config.get("info")
        nfo_div = soup.find(info_cfg.get("tag"), class_=info_cfg.get("class"))
        info = nfo_div.get_text(strip=True) if nfo_div else "No info available"

    else:

        text = soup.get_text()

        def extract(label):
            match = re.search(rf"{label}\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
            return match.group(1).strip() if match else "N/A"

        file_size = extract("Size")
        seeders = extract("Seeders")
        leechers = extract("Leechers")
        type_ = extract("Type")

        info = "No info available"

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


def download_torrent(magnet, torrent_directory: str = None):
    directory = torrent_directory or os.path.expanduser("~")
    subprocess.run(["transmission-cli", magnet, "-w", directory])


def search(
    query: str = None,
    metadata_path: str = None,
    torrent_url: str = None,
    torrent_info_mode: bool = False,
    torrent_directory: str = None,
):

    if not torrent_url:
        torrent_url = "https://thepiratebay.party/search"

    if not query:
        query = input("Enter Search Query: ")

    search_url = f"{torrent_url}/{quote(query)}"

    response = requests.get(search_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    info_links = []
    magnet_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/torrent/" in href:
            if href.startswith("/"):
                href = torrent_url + href
            info_links.append(href)

        if href.startswith("magnet:"):
            name = re.search(r"dn=([^&]+)", href)
            display = name.group(1).replace("+", " ") if name else "Unknown"
            magnet_links.append(f"{display}|{href}")

    if torrent_info_mode:
        links = info_links
    else:
        links = magnet_links

    if not links:
        logger.info("No results found.")
        return

    selection = check_fzf(links)

    mode = "INFO" if torrent_info_mode else "DOWNLOAD"
    logger.info(f"Using {mode} MODE for query: {query}.")

    if not selection:
        return

    if torrent_info_mode:
        get_torrent_metadata(selection, metadata_path)
    else:
        magnet = selection.split("|", 1)[1]
        download_torrent(magnet, torrent_directory)


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
        "-i",
        "--torrent_info_mode",
        default=os.environ.get("TORRENT_INFO_MODE", False),
        type=str_to_bool,
    )

    args = parser.parse_args()

    query = args.query
    torrent_url = args.torrent_url
    torrent_info_mode = args.torrent_info_mode
    torrent_directory = args.torrent_directory
    metadata_path = args.metadata_path
    results = search(
        query, metadata_path, torrent_url, torrent_info_mode, torrent_directory
    )
