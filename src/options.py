import os
from shutil import copy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(SCRIPT_DIR)
METADATA_DIR = os.path.join(PROJECT_PATH, "metadata")
DOWNLOADER_DIRECTORY = os.path.join(PROJECT_PATH, "downloaders", "metadata")
CONFIG_PATH = os.path.join(PROJECT_PATH, ".config")
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_PATH, ".default")


def str_to_bool(string: str):
    return string in ["1", "true", True, ""]


def _load_raw_config():
    """Loads the .config file as raw key/value string pairs."""
    config = {}

    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"File not found {CONFIG_PATH}!")

    with open(CONFIG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            value = value.strip()

            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            config[key.strip()] = value

    return config


def _write_raw_config(config_dict):
    """Writes the dict back to the .config file."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        for key, value in config_dict.items():
            f.write(f'{key}="{value}"\n')


_config_cache = None


def load_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_raw_config()
    return _config_cache


def get_option(key, default=None):
    config = load_config()

    # expand paths like ~/
    value = config.get(key, default)

    if value is None or value.strip() == "":
        value = default

    if isinstance(value, str) and value.startswith("~"):
        return os.path.expanduser(value)

    return value


def set_option(key, value):
    global _config_cache

    config = load_config()

    if key in config:
        config[key] = value

    _write_raw_config(config)
    _config_cache = config


def reset_options():
    try:
        copy(DEFAULT_CONFIG_PATH, CONFIG_PATH)
    except Exception as e:
        print(e)


def all_options():
    """Returns all config values."""
    return dict(load_config())


def options_action(
    action: str, key: str = None, value: str = None, config_path: str = None
):
    if action == "get":
        return get_option(key)
    elif action == "set":
        return set_option(key, value)
    elif action == "reset":
        reset_options()
        print("Successfully generated default downloaders.")
    else:
        return all_options()


def options_command(subparsers):
    options_cmd = subparsers.add_parser("options", help="List options")

    options_cmd.add_argument(
        "action",
        type=str,
        choices=["list", "get", "set", "reset"],
        default="list",
        nargs="?",
    )
    options_cmd.add_argument("key", type=str, nargs="?", default=None)
    options_cmd.add_argument("value", type=str, nargs="?", default=None)

    return options_cmd
