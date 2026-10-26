from pathlib import Path
import subprocess

from utils.logger import setup_logger

logger = setup_logger(name="metadata", log_dir="/udown/metadata")

import json
import mimetypes
import subprocess
from pathlib import Path


def check_tag(tag) -> str:
    """Return the tag if it looks like Tag or Group:Tag, else raise ValueError."""
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError(f"Invalid tag name: {tag!r}")

    tag = tag.strip()
    parts = tag.split(":")

    if len(parts) > 2 or not all(parts):
        raise ValueError(f"Invalid tag name: {tag!r}")

    for part in parts:
        if not all(c.isascii() and (c.isalnum() or c == "_") for c in part):
            raise ValueError(f"Invalid tag name: {tag!r}")  # wildcards, dashes, spaces

    if len(parts[-1]) < 2:
        raise ValueError(f"Tag name too short: {tag!r}")  # single letters are exiftool options

    return tag


def get_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime.split("/")[0] if mime else "other"


def read_tags(paths, tags, chunk=200):
    """One exiftool call per chunk of files -> {Path: {tag: value}}"""
    paths = list(paths)
    tags = [check_tag(t) for t in tags]
    found = {}

    for i in range(0, len(paths), chunk):
        batch = paths[i : i + chunk]
        result = subprocess.run(
            ["exiftool", "-json", *[f"-{t}" for t in tags], *map(str, batch)],
            capture_output=True,
            text=True,
        )
        try:
            entries = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            continue
        for entry in entries:
            found[Path(entry["SourceFile"])] = entry

    return found


def tag_values(entry: dict, tag: str) -> list[str]:
    """All values of a tag in one exiftool entry, as a list of strings."""
    key = tag.split(":")[-1].lower()

    for k, v in entry.items():
        if k != "SourceFile" and k.lower() == key:
            if v in (None, "", []):
                return []
            return [str(x) for x in v] if isinstance(v, list) else [str(v)]

    return []


def get_tag(file_path: Path, tag: str) -> str | None:
    entry = read_tags([file_path], [tag]).get(Path(file_path), {})
    values = tag_values(entry, tag)
    return ", ".join(values) or None


def find_by_tag(files, tag, value=None) -> dict:
    """{Path: value} for files that have the tag (and the value, if given)."""
    matches = {}

    for path, entry in read_tags(files, [tag]).items():
        values = tag_values(entry, tag)
        if not values:
            continue
        if value is None or value.lower() in (v.lower() for v in values):
            matches[path] = ", ".join(values)

    return matches


def set_tag(file_path: Path, tag: str, value: str, overwrite=True, append=False) -> None:
    """Create or update a tag. Raises ValueError or RuntimeError on failure."""
    tag = check_tag(tag)  # ValueError for an invalid tag name

    cmd = ["exiftool"]
    if overwrite:
        cmd.append("-overwrite_original")
    cmd += [f"-{tag}{'+=' if append else '='}{value}", str(file_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = (result.stdout + result.stderr).splitlines()

    if result.returncode != 0 or any(l.startswith(("Error", "Warning")) for l in lines):
        raise RuntimeError(" | ".join(lines) or f"exiftool exited with {result.returncode}")

    entry = read_tags([file_path], [tag]).get(Path(file_path), {})
    values = [v.lower() for v in tag_values(entry, tag)]
    expected = value.lower()

    if append:
        ok = expected in values
    else:
        ok = values == [expected] or ", ".join(values) == expected

    if not ok:
        raise RuntimeError(f"read back {values!r}, expected {value!r}")

def iter_files(source_directory: Path, types=None, has_tags=None) -> list[Path]:
    files = [f for f in Path(source_directory).rglob("*") if f.is_file()]

    if types:
        files = [f for f in files if get_type(f) in types]

    if has_tags:
        data = read_tags(files, has_tags)
        files = [
            f for f in files
            if all(tag_values(data.get(f, {}), t) for t in has_tags)
        ]

    return files

def read_all_tags(paths, chunk=200):
    """One exiftool call per chunk -> {Path: {"Group:Tag": value}}"""
    paths = list(paths)
    found = {}

    for i in range(0, len(paths), chunk):
        batch = paths[i : i + chunk]
        result = subprocess.run(
            ["exiftool", "-json", "-G1", *map(str, batch)],
            capture_output=True,
            text=True,
        )
        try:
            entries = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            continue
        for entry in entries:
            found[Path(entry["SourceFile"])] = entry

    return found


def search_tags(files, value, tag=None) -> dict:
    """{Path: {tag_key: value}} for every tag whose value contains `value`.

    With `tag`, only that tag is read and checked.
    """
    needle = value.lower()
    data = read_tags(files, [tag]) if tag else read_all_tags(files)
    matches = {}

    for path, entry in data.items():
        hits = {}
        for key, val in entry.items():
            # SourceFile is the path, System:* holds file name, folder, permissions
            if key == "SourceFile" or key.startswith("System:"):
                continue
            text = ", ".join(map(str, val)) if isinstance(val, list) else str(val)
            if needle in text.lower():
                hits[key] = text
        if hits:
            matches[path] = hits

    return matches

def expand_paths(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            files.append(p)
        else:
            logger.error(f"'{p}' does not exist.")
    return files


def get_metadata(files, tag, value):
    if value is not None:
        matches = search_tags(files, value, tag)
        for path, hits in matches.items():
            print(path)
            for key, found in hits.items():
                print(f"  {key} = {found}")
    else:
        matches = find_by_tag(files, tag)  # tag only: files that have it
        for path, found in matches.items():
            logger.info(f"{path}: {found}")

    logger.info(f"{len(matches)} of {len(files)} file(s) matched.")


def set_metadata(files, tag, value, append, overwrite, dry_run):
    for f in files:
        if dry_run:
            logger.info(f"DRY RUN: would set {tag}={value} on '{f}'")
            continue

        try:
            set_tag(f, tag, value, overwrite=overwrite, append=append)
            logger.info(f"Set {tag}={value} on '{f}'")
        except (ValueError, RuntimeError, OSError) as e:
            logger.error(f"Failed to set {tag} on '{f}': {e}")
      

def metadata_action(
    action=None,
    files=None,
    tag=None,
    value=None,
    append=False,
    overwrite=True,
    dry_run=False,
    **kwargs,
):
    try:
        if tag:
            tag = check_tag(tag)
    except ValueError as e:
        logger.error(f"Error: {e}")
        return None

    if action == "get":
        if not tag and value is None:
            logger.error("Error: 'get' needs --tag, --value, or both.")
            return None
        get_metadata(expand_paths(files or []), tag, value)

    elif action == "set":
        if not tag or value is None:
            logger.error("Error: 'set' needs both --tag and --value.")
            return None
        set_metadata(expand_paths(files or []), tag, value, append, overwrite, dry_run)

    return None


def metadata_command(subparsers):
    metadata_cmd = subparsers.add_parser("metadata", help="Get or set file metadata tags")

    metadata_cmd.add_argument("action", choices=["get", "set"])
    metadata_cmd.add_argument("files", nargs="+", help="Files or directories")
    metadata_cmd.add_argument("-t", "--tag", default="Keywords", help="Tag name, e.g. Keywords")
    metadata_cmd.add_argument("-v", "--value", default=None, help="Value to write (set only)")
    metadata_cmd.add_argument("--append", action="store_true",
                     help="Add to list tags (Keywords, Subject) instead of replacing")
    metadata_cmd.add_argument("--keep-original", dest="overwrite", action="store_false",
                     help="Keep exiftool's *_original backup")
    metadata_cmd.add_argument("-n", "--dry_run", "--dry-run", action="store_true")

    return metadata_cmd