
from datetime import datetime
import tempfile
import time
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from utils import str_to_bool
from utils.logger import setup_logger

logger = setup_logger(name="rename", log_dir="/udown/rename")

CHUNK_SIZE = 4 * 1024 * 1024

def stage_sources(sources, move: bool = False, dry_run: bool = False):
    """Return (source_directory, temp_dir_or_None)."""
    paths = [Path(s) for s in sources]

    for p in paths:
        if not p.exists():
            logger.error(f"Error: '{p}' does not exist.")
            sys.exit(1)

    dirs = [p for p in paths if p.is_dir()]
    files = [p for p in paths if p.is_file()]

    if len(dirs) > 1 or (dirs and files):
        logger.error("Error: pass either a single directory or one or more files.")
        sys.exit(1)

    if dirs:
        return dirs[0], None

    names = [f.name for f in files]
    if len(set(names)) != len(names):
        logger.error("Error: multiple files share the same name.")
        sys.exit(1)

    tmp = Path(tempfile.mkdtemp(prefix="rename_"))
    for f in files:
        dst = tmp / f.name
        if dry_run:
            dst.symlink_to(f.resolve())  # nothing is copied or moved
        elif move:
            shutil.move(f, dst)
        else:
            shutil.copy2(f, dst)

    return tmp, tmp


def cleanup_staging(tmp: Path | None, move: bool, dry_run: bool):
    if tmp is None:
        return

    # In move mode, anything left in tmp failed to move and is the only copy
    leftovers = [f for f in tmp.rglob("*") if f.is_file()]
    if move and leftovers and not dry_run:
        logger.warning(f"{len(leftovers)} file(s) were not moved, keeping {tmp}")
        return

    shutil.rmtree(tmp, ignore_errors=True)
    
def format_bytes(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def print_progress(
    done, total, dry_run: bool = False, progress: bool = True, prefix="", bar_length=30
):
    if dry_run:
        return

    if not progress:
        return

    fraction = done / total if total else 1
    filled = int(bar_length * fraction)
    bar = "█" * filled + "-" * (bar_length - filled)
    percent = int(fraction * 100)

    sys.stdout.write(f"\r{prefix}[{bar}] {percent:3d}% ({done}/{total})")
    sys.stdout.flush()

    if done == total:
        print()


def print_byte_progress(
    done,
    total,
    start_time,
    filename="",
    dry_run: bool = False,
    progress: bool = True,
    bar_length=30,
):
    if dry_run:
        return

    if not progress:
        return

    fraction = done / total if total else 1
    filled = int(bar_length * fraction)
    bar = "█" * filled + "-" * (bar_length - filled)
    percent = int(fraction * 100)

    elapsed = time.time() - start_time
    speed = done / elapsed if elapsed > 0 else 0

    sys.stdout.write(
        f"\r[{bar}] {percent:3d}% "
        f"{format_bytes(done)}/{format_bytes(total)} "
        f"({format_bytes(speed)}/s) {filename}"
    )
    sys.stdout.flush()

def copy_files(files, destination_path, dry_run=False, progress=False, use_chunks=False):
    destination = Path(destination_path)
    new_files = [destination / f.name for f in files]
    move_files(files, new_files, move=False, dry_run=dry_run,
               progress=progress, use_chunks=use_chunks)
    

def copy2_with_progress(src, dst, dry_run: bool = False, progress: bool = True):
    total_size = os.path.getsize(src)
    done = 0
    start_time = time.time()

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        while True:
            chunk = fsrc.read(CHUNK_SIZE)
            if not chunk:
                break
            fdst.write(chunk)
            done += len(chunk)
            print_byte_progress(
                done, total_size, start_time, os.path.basename(src), dry_run, progress
            )

    shutil.copystat(src, dst)
    print()


def get_exif_year(file_path: Path) -> str | None:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        return None

    if mime_type.startswith("video"):
        tags = ["MediaCreateDate", "TrackCreateDate", "CreateDate"]
    elif mime_type.startswith("image"):
        tags = ["DateTimeOriginal", "CreateDate"]
    else:
        return None

    for tag in tags:
        try:
            result = subprocess.run(
                ["exiftool", "-s3", f"-{tag}", "-d", "%Y", str(file_path)],
                capture_output=True,
                text=True,
            )
            year = result.stdout.strip()
            if year and year.isdigit() and len(year) == 4:
                return year
        except Exception as e:
            logger.error(f"{e}")
            continue

    return None


def get_modification_year(file_path):
    try:
        timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(timestamp).strftime("%Y")
    except Exception:
        return None


def create_backup(
    source_directory: Path,
    backup_directory: str = None,
    dry_run: bool = False,
    backup: bool = False,
):

    dest = None

    if not backup:
        return

    if not backup_directory:
        backup_directory = "/tmp/backup"

    try:
        logger.info(f"Creating backup at {backup_directory}")

        if not dry_run:
            dest = shutil.copytree(
                source_directory, backup_directory, dirs_exist_ok=True
            )
            logger.info(f"Successfully created backup {dest}.")

    except Exception as e:
        logger.error(f"Exception: {e}")

    return dest


def get_directory_as_path(directory: str):
    if isinstance(directory, str):
        directory = Path(directory)

    if not directory.is_dir():
        logger.error(f"Error: '{directory}' is not a directory.")
        sys.exit(1)

    return directory


def diff_paths(old_file: Path, new_file: Path):
    old_parts = old_file.parts
    new_parts = new_file.parts

    i = 0
    for o, n in zip(old_parts, new_parts):
        if o != n:
            break
        i += 1

    old_diff = Path(*old_parts[i:])
    new_diff = Path(*new_parts[i:])

    return str(old_diff), str(new_diff)


def move_files(
    old_files: list,
    new_files: list,
    move: bool,
    dry_run: bool,
    progress: bool = False,
    use_chunks: bool = False,
):

    if dry_run:
        logger.warning("DRY RUN MODE: No changes will be applied.")

    total_files = len(old_files)
    processed_files = 0

    for old_file, new_file in zip(old_files, new_files):
        action = "Moving" if move else "Copying"

        src, dst = diff_paths(old_file, new_file)

        logger.info(f"{action} '{src}' -> '{dst}'")

        if not dry_run:  # move only if dry run is false
            new_file.parent.mkdir(parents=True, exist_ok=True)  # ensure folder exists

            try:
                if use_chunks:
                    copy2_with_progress(
                        old_file, new_file, dry_run=dry_run, progress=progress
                    )
                    if move:
                        os.remove(old_file)
                else:
                    if move:
                        shutil.move(old_file, new_file)
                    else:
                        shutil.copy2(old_file, new_file)

            except Exception as e:
                print(e)

        if not use_chunks:
            processed_files += 1
            print_progress(
                processed_files, total_files, dry_run, progress, prefix="Files: "
            )

    return old_files, new_files


def rename_by_year(
    source_directory: Path, destination_directory: Path, dry_run: bool
):

    old_files = []
    new_files = []

    for file_path in source_directory.rglob("*"):
        if file_path.is_file():
            year = get_exif_year(file_path)
            if not year:
                year = get_modification_year(file_path)

            if not year:
                logger.error(f"Warning: Could not determine year for '{file_path}'")
                continue

            target_dir = destination_directory / year

            if not target_dir.exists() and not dry_run:
                logger.info(f"Created year directory {target_dir}.")
                target_dir.mkdir(parents=True, exist_ok=True)

            rel_path = file_path.relative_to(source_directory)
            dest_path = target_dir / rel_path

            old_files.append(file_path)
            new_files.append(dest_path)

    return old_files, new_files


def rename_by_pattern(
    source_directory: Path,
    destination_directory: Path,
    pattern: str = None,
    repl: str = None,
):
    old_files = []
    new_files = []

    logger.info(f"Using pattern: {pattern}")
    logger.info(f"Repl: {repl}")

    for file_path in source_directory.rglob("*"):
        if file_path.is_file():
            if pattern and repl:
                new_stem = re.sub(pattern, repl, file_path.stem, flags=re.IGNORECASE)
            else:
                new_stem = file_path.stem

            new_name = f"{new_stem}{file_path.suffix}"

            rel_path = file_path.relative_to(source_directory)
            dest_path = destination_directory / rel_path.parent / new_name

            old_files.append(file_path)
            new_files.append(dest_path)

    return old_files, new_files


def rename_files(
    sources,
    destination_directory: str = None,
    action: str = None,
    pattern: str = None,
    repl: str = None,
    move: bool = False,
    backup: bool = False,
    backup_directory: str = None,
    use_chunks: bool = False,
    progress: bool = False,
    dry_run: bool = False,
):

    if sources is None:
        sources = []
    elif isinstance(sources, (str, Path)):
        sources = [sources]
        
    sources = [Path(s) for s in sources] or [Path.cwd()]

    if not destination_directory:
        if sources[0].is_dir():
            destination_directory = sources[0]  # rename in place
        else:
            parents = {s.resolve().parent for s in sources}
            if len(parents) > 1:
                logger.error("Error: files are in different folders, pass -o.")
                sys.exit(1)
            destination_directory = parents.pop()  # next to the originals

    source_directory, tmp = stage_sources(sources, move, dry_run)
    destination_directory = get_directory_as_path(destination_directory)


    try:
        create_backup(source_directory, backup_directory, dry_run, backup)

        new_files = []
        old_files = []

        logger.info(f"Action: {action}")

        if action == "year":
            old_files, new_files = rename_by_year(
                source_directory, destination_directory, dry_run
            )
        elif action == "episodes":
            pattern = r".*?(S\d{2}E\d{2}|\d{1,5}).*"  # pattern for episodes
            repl = r"\1"
            old_files, new_files = rename_by_pattern(
                source_directory, destination_directory, pattern, repl
            )
        elif action == "prefix":
            pattern = r"^(.*)$"

            if not repl:
                prefix = input("Prefix: ")
                if prefix:
                    repl = f"{prefix}\\1"
                else:
                    repl = r"\1"

            old_files, new_files = rename_by_pattern(
                source_directory, destination_directory, pattern, repl
            )
        elif action == "suffix":
            pattern = r"^(.*?)(\.[^.]+)?$"

            if not repl:
                suffix = input("Suffix: ")
                if suffix:
                    repl = r"\1" + suffix + r"\2"
                else:
                    repl = r"\1\2"

            old_files, new_files = rename_by_pattern(
                source_directory, destination_directory, pattern, repl
            )
        else:
            old_files, new_files = rename_by_pattern(
                source_directory, destination_directory, pattern, repl
            )

        move_files(old_files, new_files, move, dry_run, progress, use_chunks)
        return old_files, new_files
    finally:
        cleanup_staging(tmp, move, dry_run)

def rename_action(
    sources = None,
    destination_directory=None,
    action=None,
    pattern=None,
    repl=None,
    move=False,
    backup=False,
    backup_directory=None,
    use_chunks=False,
    progress=False,
    dry_run=False,
    **kwargs,
):
    return rename_files(
        sources=sources or [os.getcwd()],
        destination_directory=destination_directory,
        action=action,
        pattern=pattern,
        repl=repl,
        move=move,
        backup=backup,
        backup_directory=backup_directory,
        use_chunks=use_chunks,
        progress=progress,
        dry_run=dry_run,
    )


def rename_command(subparsers):
    rename_cmd = subparsers.add_parser(
        "rename",
        help="Bulk rename and organize files",
    )

    rename_cmd.add_argument("sources", nargs="*", default=os.getcwd())
    rename_cmd.add_argument(
        "-d", "--destination_directory",
        nargs="?",
        default=None,
        type=str,
    )
    rename_cmd.add_argument(
        "-a",
        "--action",
        choices=["pattern", "episodes", "prefix", "suffix", "year"],
        default=os.environ.get("RENAME_ACTION"),
    )
    rename_cmd.add_argument("-p", "--pattern", default=None)
    rename_cmd.add_argument("-r", "--repl", default=None)

    rename_cmd.add_argument(
        "-m", "--move",
        nargs="?",
        const=True,
        type=str_to_bool,
        default=os.environ.get("MOVE_FILES", False),
    )
    rename_cmd.add_argument(
        "-n", "--dry_run", "--dry-run",
        nargs="?",
        const=True,
        type=str_to_bool,
        default=os.environ.get("DRY_RUN", False),
    )
    rename_cmd.add_argument(
        "-b", "--backup",
        nargs="?",
        const=True,
        type=str_to_bool,
        default=os.environ.get("BACKUP", False),
    )
    rename_cmd.add_argument(
            "-bd", "--backup_directory",
            default=os.environ.get("BACKUP_DIRECTORY"),
    )
    rename_cmd.add_argument(
        "-c", "--use_chunks",
        nargs="?",
        const=True,
        type=str_to_bool,
        default=os.environ.get("USE_CHUNKS", False),
    )
    rename_cmd.add_argument(
        "--progress",
        nargs="?",
        const=True,
        type=str_to_bool,
        default=False,
    )

    return rename_cmd