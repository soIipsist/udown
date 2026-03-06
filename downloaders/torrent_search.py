import os
import re
import subprocess
from urllib.parse import quote
from argparse import ArgumentParser
import requests
from bs4 import BeautifulSoup


def get_torrent_metadata(torrent_url):
    response = requests.get(torrent_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    details_div = soup.find("div", id="details")
    if not details_div:
        print("No details found.")
        return

    def get_detail(label):
        dt = details_div.find("dt", string=re.compile(label))
        if dt and dt.find_next_sibling("dd"):
            return dt.find_next_sibling("dd").get_text(strip=True)
        return "N/A"

    file_size = get_detail("Size")
    seeders = get_detail("Seeders")
    leechers = get_detail("Leechers")
    type_ = get_detail("Type")

    nfo_div = soup.find("div", class_="nfo")
    info = nfo_div.get_text(strip=True) if nfo_div else "No info available"

    print("==============================")
    print(" Torrent Metadata")
    print("==============================")
    print(f" Type     : {type_}")
    print(f" Size     : {file_size}")
    print(f" Seeders  : {seeders}")
    print(f" Leechers : {leechers}")
    print("------------------------------")
    print(" Info:")
    print(info)
    print("------------------------------")
    print(f"URL: {torrent_url}")
    print("==============================")


def download_torrent(magnet, torrent_directory: str = None):
    directory = torrent_directory or os.path.expanduser("~")
    subprocess.run(["transmission-cli", magnet, "-w", directory])


def torrent(query=None, torrent_url: str = None, torrent_info_mode: int = 0):

    if not query:
        query = input("Enter Search Query: ")

    search_url = f"{torrent_url}/{quote(query)}"
    print(search_url)

    response = requests.get(search_url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    info_links = []
    magnet_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/torrent/" in href:
            if href.startswith("/"):
                href = "https://thepiratebay.party" + href
            info_links.append(href)

        if href.startswith("magnet:"):
            name = re.search(r"dn=([^&]+)", href)
            display = name.group(1).replace("+", " ") if name else "Unknown"
            magnet_links.append(f"{display}|{href}")

    if torrent_info_mode == 1:
        links = info_links
    else:
        links = magnet_links

    if not links:
        print("No results found.")
        return

    fzf = subprocess.Popen(
        ["fzf"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )

    stdout, _ = fzf.communicate("\n".join(links))
    selection = stdout.strip()

    if not selection:
        return

    if torrent_info_mode == 1:
        get_torrent_metadata(selection)
        subprocess.run(["less"], input="", text=True)
    else:
        magnet = selection.split("|", 1)[1]
        download_torrent(magnet)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument(
        "-u", "--torrent_url", type=str, default=os.environ.get("TORRENT_URL")
    )
    parser.add_argument(
        "-d",
        "--torrent_directory",
        type=str,
        default=os.environ.get("TORRENT_DIRECTORY"),
    )

    args = parser.parse_args()

    query = args.query
    torrent_url = args.torrent_url
    torrent_info_mode = args.torrent_info_mode
    results = torrent(query, torrent_url, torrent_info_mode)
