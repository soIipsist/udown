import argparse
import re
import subprocess
import sys
from pathlib import Path
from pprint import PrettyPrinter
from utils.logger import setup_logger

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="transmission", log_dir="/udown/transmission")

PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)%")
SPEED_RE = re.compile(r"Down:\s*([\d.]+\s*[KMG]?B/s)", re.I)
UPLOAD_RE = re.compile(r"Up:\s*([\d.]+\s*[KMG]?B/s)", re.I)
PEERS_RE = re.compile(r"Peers:\s*(\d+)", re.I)
ETA_RE = re.compile(r"ETA\s*([^\s|]+)", re.I)
RATIO_RE = re.compile(r"Ratio:\s*([\d.]+)", re.I)


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
            "status": None,
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

                percent_match = PERCENT_RE.search(line)
                if not percent_match:
                    continue

                percent = float(percent_match.group(1))
                if percent == last_percent:
                    continue

                parts = []

                speed_match = SPEED_RE.search(line)
                if speed_match:
                    parts.append(f"↓ {speed_match.group(1)}")

                upload_match = UPLOAD_RE.search(line)
                if upload_match:
                    parts.append(f"↑ {upload_match.group(1)}")

                peers_match = PEERS_RE.search(line)
                if peers_match:
                    parts.append(f"Peers {peers_match.group(1)}")

                eta_match = ETA_RE.search(line)
                if eta_match:
                    parts.append(f"ETA {eta_match.group(1)}")

                bar = _render_progress(percent)
                line_out = bar

                if parts:
                    line_out += " | " + " | ".join(parts)

                sys.stdout.write("\r" + line_out)
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
                result["status"] = 0

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
