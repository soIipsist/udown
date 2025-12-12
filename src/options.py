import os

CONFIG_PATH = os.path.expanduser("~/.udown/config")


def _load_raw_config():
    """Loads the .config file as raw key/value string pairs."""
    config = {}

    if not os.path.exists(CONFIG_PATH):
        return config

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
    if isinstance(value, str) and value.startswith("~"):
        return os.path.expanduser(value)

    return value


def set_option(key, value):
    global _config_cache

    config = load_config()
    config[key] = value

    _write_raw_config(config)
    _config_cache = config


def all_options():
    """Returns all config values."""
    return dict(load_config())
