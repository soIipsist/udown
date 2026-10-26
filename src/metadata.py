from pathlib import Path
import subprocess

from utils.logger import setup_logger

logger = setup_logger(name="metadata", log_dir="/udown/metadata")


def get_tag(file_path: Path, tag: str) -> str | None:
    result = subprocess.run(
        ["exiftool", "-s3", f"-{tag}", str(file_path)],
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or None

def set_tag(file_path, tag, value, overwrite=True, append=False):

    cmd = ["exiftool"]
    if overwrite:
        cmd.append("-overwrite_original")
    op = "+=" if append else "="
    cmd += [f"-{tag}{op}{value}", str(file_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr

    if result.returncode != 0 or "Error" in output or "Warning" in output:
        return False

    current = get_tag(file_path, tag)
    if current is None:
        return False

    return value in current if append else current == value

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
    if not tag:
        logger.error("Error: --tag is required.")
        return None

    if action == "set" and value is None:
        logger.error("Error: --value is required for 'set'.")
        return None

    for f in expand_paths(files or []):
        if action == "get":
            print(f"{f}: {tag} = {get_tag(f, tag)}")

        elif action == "set":
            if dry_run:
                logger.info(f"DRY RUN: would set {tag}={value} on '{f}'")
                continue

            ok = set_tag(f, tag, value, overwrite=overwrite, append=append)
            logger.info(f"{'Set' if ok else 'Failed to set'} {tag}={value} on '{f}'")

    return None


def metadata_command(subparsers):
    metadata_cmd = subparsers.add_parser("metadata", help="Get or set file metadata tags")

    metadata_cmd.add_argument("action", choices=["get", "set"])
    metadata_cmd.add_argument("files", nargs="+", help="Files or directories")
    metadata_cmd.add_argument("-t", "--tag", default=None, help="Tag name, e.g. Keywords")
    metadata_cmd.add_argument("-v", "--value", default=None, help="Value to write (set only)")
    metadata_cmd.add_argument("--append", action="store_true",
                     help="Add to list tags (Keywords, Subject) instead of replacing")
    metadata_cmd.add_argument("--keep-original", dest="overwrite", action="store_false",
                     help="Keep exiftool's *_original backup")
    metadata_cmd.add_argument("-n", "--dry_run", "--dry-run", action="store_true")

    return metadata_cmd