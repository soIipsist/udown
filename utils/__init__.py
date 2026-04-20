import ast
import json
from datetime import datetime, timedelta
import re
from urllib.parse import urlsplit


def parse_date(date: str):
    now = datetime.now()
    date_clean = date.lower().strip()

    result = None

    if date_clean == "today":
        result = now
    elif date_clean == "yesterday":
        result = now - timedelta(days=1)
    elif date_clean == "tomorrow":
        result = now + timedelta(days=1)
    else:
        match = re.match(r"(\d+)\s+days?\s+ago", date_clean)
        if match:
            days = int(match.group(1))
            result = now - timedelta(days=days)

    if result:
        return result.strftime("%Y-%m-%d")

    return date


def parse_value(value):
    value = value.strip()

    # return as string (without quotes)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    try:
        return ast.literal_eval(value)
    except Exception:
        return value


def str_to_bool(string: str):
    return string in ["1", "true", True, ""]


def read_file(file_path, encoding="utf-8", errors=None, logger=None):
    """
    Returns a file object.
    """

    try:
        with open(file_path, "r", encoding=encoding, errors=errors) as file:
            return file.read()

    except FileNotFoundError:
        raise ValueError("File not found")

    except (ValueError, Exception) as e:
        logger.error(f"An error occurred: {e}, {e.__class__}")


def read_json_file(json_file, errors=None, logger=None):
    try:
        with open(json_file, "r", errors=errors) as file:
            json_object = json.load(file)
            return json_object
    except Exception as e:
        logger.error(str(e))


def is_valid_url(url: str) -> bool:
    """Check if a given string is a valid URL (has scheme and netloc)."""
    if not url:
        return False
    try:
        parsed = urlsplit(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False
