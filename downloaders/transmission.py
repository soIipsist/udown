import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from pprint import PrettyPrinter

from utils.logger import setup_logger

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="transmission", log_dir="/udown/transmission")

PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)%")


def _render_progress(percent: float, width: int = 30) -> str:
    filled = int(width * percent / 100)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {percent:6.2f}%"


def download(
    urls: list | str,
    output_directory: str = None,
) -> list[dict]:

    if isinstance(urls, str):
        urls = [urls]

    results = []

    out_dir = Path(output_directory or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        logger.info(f"Starting download: {url}")

        result = {
            "url": url,
            "status": 0,
            "path": None,
            "stdout": "",
            "error": None,
        }

        cmd = ["transmission-cli", url, "-w", str(out_dir)]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            stdout_lines: list[str] = []
            last_percent = -1.0

            for line in process.stdout:
                stdout_lines.append(line)

                match = PERCENT_RE.search(line)
                if not match:
                    continue

                percent = float(match.group(1))
                if percent != last_percent:
                    bar = _render_progress(percent)
                    sys.stdout.write("\r" + bar)
                    sys.stdout.flush()
                    last_percent = percent

            process.wait()
            sys.stdout.write("\n")

            result["stdout"] = "".join(stdout_lines)
            result["status"] = process.returncode

            if process.returncode != 0:
                error = f"transmission-cli exited with code {process.returncode}"
                logger.error(error)
                result["error"] = error
            else:
                logger.info("Download completed successfully")
                result["path"] = str(out_dir)

        except KeyboardInterrupt:
            logger.warning("Download interrupted by user")
            result["status"] = 1
            result["error"] = "Interrupted by user"

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            result["status"] = 1
            result["error"] = str(e)

        results.append(result)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download torrents using transmission-cli"
    )
    parser.add_argument("urls", nargs="+", type=str, help="Torrent or magnet URLs")
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )

    args = parser.parse_args()

    results = download(
        args.urls,
        args.output_directory,
    )

    pp.pprint(results)
