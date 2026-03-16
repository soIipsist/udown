import subprocess
import sys
from src.downloader import Downloader, default_downloaders

UDOWN_GIT = "git+https://github.com/youruser/udown.git"


def pip_upgrade(package):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", package],
        check=True,
    )


def update_action(package=None, **args):
    # reset downloaders
    Downloader.reset_all(default_downloaders)

    # update dependencies
    if package:
        pip_upgrade(package)
    else:
        pip_upgrade(UDOWN_GIT)


def update_command(subparsers):
    update_cmd = subparsers.add_parser("update", help="Update udown")
    update_cmd.add_argument(
        "package",
        nargs="?",
        help="Package to update (default: udown)",
    )
    return update_cmd
