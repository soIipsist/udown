import subprocess
import sys
from src.downloader import Downloader
from src.download import Download

UDOWN_GIT = "git+https://github.com/soIipsist/udown.git"
default_packages = [
    UDOWN_GIT,
    "yt-dlp",
    "selenium",
    "undetected-chromedriver",
    "beautifulsoup4",
    "requests",
    "urllib3",
    "lxml",
]


def pip_upgrade(packages: list):

    if isinstance(packages, str):
        packages = [packages]

    for package in packages:
        if package in default_packages:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", package],
                check=True,
            )


def update_action(packages=None, **args):

    # get existing items before updating
    existing_downloads = Download().select_all()
    existing_downloaders = Downloader().select_all()

    # update dependencies
    if packages:
        pip_upgrade(packages)
    else:
        pip_upgrade(default_packages)

    # reset items
    Downloader.reset_all(existing_downloaders)
    Download.insert_all(existing_downloads)

def update_command(subparsers):
    update_cmd = subparsers.add_parser("update", help="Update udown")
    update_cmd.add_argument(
        "packages",
        nargs="*",
        type=str,
        default=None,
        help="Packages to update (default: udown)",
    )
    return update_cmd
