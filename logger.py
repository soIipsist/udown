from datetime import datetime
import logging
import os
from pathlib import Path
import stat


LOG_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",  # Reset to default
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        color = LOG_COLORS.get(levelname, "")
        reset = LOG_COLORS["RESET"]
        record.levelname = f"{color}{levelname}{reset}"
        return super().format(record)


def setup_logger(name="downloader", log_dir="/tmp", level=logging.INFO):

    uid = os.getuid()

    # Build per-user tmp path
    log_dir = Path(log_dir).expanduser().resolve()
    if log_dir.is_absolute():
        log_dir = Path(*log_dir.parts[1:])
    per_user_log_dir = Path("/tmp") / str(uid) / log_dir

    if not per_user_log_dir.exists():
        per_user_log_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(per_user_log_dir, 0o700)

    log_file = per_user_log_dir / f"{name}_{datetime.now():%Y-%m-%d}.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler.setFormatter(formatter)

        color_formatter = ColoredFormatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(color_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
