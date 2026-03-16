from src.downloader import Downloader, default_downloaders


def update_action(**args):
    pass


def update_command(subparsers):
    Downloader.reset_all(default_downloaders)

    # update pyproject.toml dependencies
