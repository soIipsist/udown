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
from downloaders.ytdlp import str_to_bool
from utils.logger import setup_logger
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


def normalize_magnet(magnet: str) -> str:
    magnet = magnet.strip()
    parsed = urlparse(magnet)

    if parsed.scheme != "magnet":
        raise ValueError("Not a magnet link")

    params = parse_qs(parsed.query)

    xt = params.get("xt")
    normalized = f"magnet:?xt={xt[0]}"

    dn_list = params.get("dn")
    display_name = None
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
    magnet: str,
    value: str,
    torrent_directory: str = None,
    confirm_download: bool = False,
):
    if magnet.startswith("magnet"):
        magnet, display_name = normalize_magnet(magnet)
    else:
        display_name = None

    logger.info(f"Torrent: {magnet}")

    result = {
        "url": value if value else magnet,
        "status": None,
        "output_filename": display_name,
        "stdout": "",
        "error": None,
    }

    if confirm_download:
        input_str = (
            f"Downloading magnet '{magnet}' from {value}. Proceed? (y/n): "
            if value
            else f"Downloading magnet '{magnet}'. Proceed? (y/n): "
        )
        answer = input(input_str).strip().lower()
        if answer != "y":
            result["status"] = 1
            result["error"] = "Cancelled"
            return [result]

    directory = torrent_directory or os.path.expanduser("~")
    placeholder = "/tmp/transmission-finish-placeholder.sh"

    cmd = [
        "transmission-cli",
        magnet,
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
        logger.error(f"Failed to download {magnet}: {e}")
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


def extract_links(base_url: str, page_response, patterns):
    info_pattern = patterns.get("info", "/torrent/")
    magnet_pattern = patterns.get("magnet", "magnet:")

    info_links = []
    magnet_links = []

    soup = BeautifulSoup(page_response, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if info_pattern and info_pattern in href:
            display = link.get_text(strip=True) or href
            url = urljoin(base_url, href)
            info_links.append(f"{display}|{url}")

        if magnet_pattern and magnet_pattern in href:
            magnet = href

            name = re.search(r"dn=([^&]+)", magnet)
            display = unquote(name.group(1)) if name else "Unknown"
            magnet_links.append(f"{display}|{magnet}")

    return info_links, magnet_links


def search(
    query: str = None,
    metadata_path: str = None,
    torrent_url: str = None,
    torrent_info_mode: bool = False,
    torrent_directory: str = None,
):
    metadata = None
    info_links = []
    magnet_links = []

    if metadata_path and os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

    if not torrent_url:
        torrent_url = "https://thepiratebay.party/search"

    metadata = metadata.get(torrent_url, {})

    if not query:
        query = input("Enter Search Query: ")

    # if it's a magnet or a torrent file, simply download
    if query.startswith("magnet:") or query.endswith(".torrent"):
        results = download_torrent(query, None, torrent_directory, True)
        return results

    search_url = build_search_url(torrent_url, query)
    logger.info(f"Search url: {search_url}")

    use_selenium = metadata.get("use_selenium", False)
    patterns = metadata.get("patterns", {})
    page_response = get_page_response(search_url, use_selenium)
    search_info_links, search_magnet_links = extract_links(
        search_url, page_response, patterns
    )

    info_links.extend(search_info_links)
    magnet_links.extend(search_magnet_links)

    if torrent_info_mode:
        links = info_links
    else:
        links = magnet_links if magnet_links else info_links

    if not links:
        logger.info("No results found.")
        return

    selection = check_fzf(links)
    mode = "INFO" if torrent_info_mode else "DOWNLOAD"
    logger.info(f"Using {mode} MODE for query: {query}.")
    logger.info(f"Selection: {selection}")

    if not selection:
        return

    if torrent_info_mode:
        url = selection.split("|", 1)[1]
        get_torrent_metadata(url, use_selenium, metadata)
        results = []
    else:
        confirm_download = False
        value = selection.split("|", 1)[1]
        if value.startswith("magnet:"):
            magnet = value
        else:
            logger.info("Magnet not found on search page, checking details page...")
            detail_page = get_page_response(value, use_selenium)
            _, detail_magnets = extract_links(value, detail_page, patterns)

            if not detail_magnets:
                logger.error("No magnet link found on details page.")
                return

            magnet = detail_magnets[0].split("|", 1)[1]
            confirm_download = True

        results = download_torrent(magnet, value, torrent_directory, confirm_download)

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
