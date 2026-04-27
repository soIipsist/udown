from pathlib import Path
import os
from downloaders.torrent import *
from test_base import *
from src.settings import DOWNLOADER_METADATA_DIR
from utils.logger import write_output

current_file = Path(__file__).resolve()
parent_directory = current_file.parents[2]
os.sys.path.insert(0, str(parent_directory))


pp = PrettyPrinter(indent=2)
import subprocess

magnet = "magnet:?xt=urn:btih:0123456789ABCDEF0123456789ABCDEF01234567&dn=Sample+File&tr=udp%3A%2F%2Ftracker.example.com%3A1337%2Fannounce"
torrent_file = os.path.abspath(
    os.path.expanduser("~/Downloads/BigBuckBunny_124_archive.torrent")
)
torrent_link = ""

torrent_urls = [
    "https://thepiratebay.party/search",
    "https://thepiratebay.org/search.php?q=",
    "https://kickasstorrents.to/usearch",
    "https://archive.org/search.php?query=",
]
torrent_url = torrent_urls[2]

patterns_arr = [
    {"info": "/torrent", "magnet": "magnet:"},
    {"info": "/description", "magnet": "magnet:"},
    {"info": "-t", "magnet": "magnet:", "torrent": "/download/"},
]
patterns = patterns_arr[2]


# def check_fzf(links):

#     proc = subprocess.run(
#         ["fzf", "--expect=ctrl-i"],
#         input="\n".join(links),
#         text=True,
#         capture_output=True,
#     )

#     lines = proc.stdout.splitlines()

#     if not lines:
#         return None, None

#     if lines[0] == "ctrl-i":
#         selection = lines[1] if len(lines) > 1 else None
#         return "toggle", selection

#     return "select", lines[0]


def simple_two_list_toggle():
    cmd = r"""
fzf --prompt="List A > " \
    --header="Ctrl+S = toggle" \
    --bind 'ctrl-s:reload(echo "second list item 1\nsecond list item 2")+change-prompt(List B > )' \
    --bind 'ctrl-i:reload(echo "first list item 1\nfirst list item 2")+change-prompt(List A > )'
"""
    subprocess.run(cmd, shell=True, executable="/bin/bash")


class TestTorrent(TestBase):
    def setUp(self) -> None:
        super().setUp()

    def test_check_fzf(self):
        simple_two_list_toggle()

        magnet_links = []
        info_links = []

        # links = [
        #     "Ubuntu ISO|magnet:123",
        #     "Arch Linux|magnet:456",
        #     "Debian|magnet:789",
        # ]

        # action, selection = check_fzf(links)

        # print("ACTION:", action)
        # print("SELECTION:", selection)

    def test_download_torrent(self):
        torrent = torrent_file
        torrent_directory = os.getcwd()
        confirm_download = True

        print(torrent)
        self.assertTrue(os.path.exists(torrent))

        results = download_torrent(
            torrent,
            torrent_directory=torrent_directory,
            confirm_download=confirm_download,
            normalize=True,
        )
        print(results)

    def test_normalize_magnet(self):
        normalized_magnet = normalize_magnet(magnet, normalize=False)
        print(normalized_magnet)

    def test_build_search_url(self):
        cases = [
            # {query} placeholder
            (
                "https://example.com/search/{query}",
                "hello world",
                f"https://example.com/search/{quote('hello world')}",
            ),
            # endswith "="
            (
                "https://example.com/search?q=",
                "hello world",
                f"https://example.com/search?q={quote('hello world')}",
            ),
            # has "?" but not "=" at end
            (
                "https://example.com/search?page=1",
                "hello world",
                f"https://example.com/search?page=1&q={quote('hello world')}",
            ),
            # endswith "/"
            (
                "https://example.com/search/",
                "hello world",
                f"https://example.com/search/{quote('hello world')}",
            ),
            # default case
            (
                "https://example.com/search",
                "hello world",
                f"https://example.com/search/{quote('hello world')}",
            ),
            # encoding edge case
            (
                "https://example.com/search/",
                "a+b & c/d",
                f"https://example.com/search/{quote('a+b & c/d')}",
            ),
        ]

        for base_url, query, expected in cases:
            with self.subTest(base_url=base_url, query=query):
                result = build_search_url(base_url, query)
                self.assertEqual(result, expected)
                print(result, expected)

    def test_get_page_response(self):
        search_url = build_search_url(torrent_url, "action")
        page_response = get_page_response(search_url, False)
        write_output(logger, page_response, "index.html", append=False)
        self.assertTrue(os.path.exists("index.html"))

    def test_extract_links(self):
        page_name = os.path.basename(torrent_url)

        search_url = build_search_url(torrent_url, "action")

        search_url = (
            "https://kickasstorrents.to/9-1-1-s09e14-hdtv-x264-ngp-t6608005.html"
        )

        page_response = get_page_response(search_url, False)
        write_output(logger, page_response, f"{page_name}.html", append=False)
        self.assertTrue(os.path.exists(f"{page_name}.html"))

        links = extract_links(page_response, patterns)
        magnet_links = Link.filter_by_type(links, LinkType.MAGNET)

        check_fzf(magnet_links)

    def test_download_torrent_from_url(self):

        torrent_url = "https://archive.org/download/BigBuckBunny_124/BigBuckBunny_124_archive.torrent"
        torrent_directory = None
        torrent_path = download_torrent_from_url(torrent_url, torrent_directory)

        self.assertTrue(os.path.exists(torrent_path))

    def test_search(self):
        # results = search("limitless", None, torrent_urls[0], torrent_mode="magnet")
        # print(results)

        # results = search("limitless", None, torrent_urls[1], torrent_mode="torrent")

        results = search("limitless", None, torrent_urls[1], torrent_mode="torrent")


if __name__ == "__main__":
    test_methods = [
        # TestTorrent.test_check_fzf,
        # TestTorrent.test_normalize_magnet,
        # TestTorrent.test_build_search_url,
        # TestTorrent.test_get_page_response,
        # TestTorrent.test_download_torrent,
        # TestTorrent.test_download_torrent_from_url,
        # TestTorrent.test_extract_links,
        TestTorrent.test_search,
    ]
    run_test_methods(test_methods)
