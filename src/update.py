import subprocess
import sys
from src.downloader import Downloader, default_downloaders

UDOWN_GIT = "git+https://github.com/soIipsist/udown.git"
default_packages = [UDOWN_GIT, "yt-dlp", "selenium", "beautifulsoup4", "requests"]


def pip_upgrade(packages: list):

    if isinstance(packages, str):
        packages = [packages]

    for package in packages:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", package],
            check=True,
        )


def update_action(packages=None, **args):
    # reset downloaders
    Downloader.reset_all(default_downloaders)

    # update dependencies
    if packages:
        pip_upgrade(packages)
    else:
        pip_upgrade(default_packages)


def update_command(subparsers):
    update_cmd = subparsers.add_parser("update", help="Update udown")
    update_cmd.add_argument(
        "packages",
        nargs="?",
        help="Packages to update (default: udown)",
    )
    return update_cmd
