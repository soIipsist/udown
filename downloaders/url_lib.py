import argparse
import os
from pprint import PrettyPrinter
import urllib3
from urllib.parse import urlparse
from pathlib import Path
from utils.logger import setup_logger

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

pp = PrettyPrinter(indent=2)
logger = setup_logger(name="url_lib", log_dir="/udown/url_lib")


def download(
    urls: list | str,
    output_directory: str = None,
    output_filename: str = None,
    user_agent: str = None,
    headers: dict = None,
) -> list[dict]:
    """
    Download files using urllib3 with progress logging via logger.
    Returns list of results.
    """
    if isinstance(urls, str):
        urls = [urls]

    headers = (headers or DEFAULT_HEADERS).copy()
    if user_agent:
        headers["User-Agent"] = user_agent

    http = urllib3.PoolManager(headers=headers)
    results = []

    for url in urls:
        logger.info(f"Starting download: {url}")
        result = {"url": url, "status": 0}

        try:
            parsed = urlparse(url)
            filename = (
                output_filename or os.path.basename(parsed.path) or "downloaded_file"
            )
            out_dir = Path(output_directory or ".")
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / filename

            logger.info(f"→ Saving to: {output_path}")

            response = http.request("GET", url, preload_content=False, retries=False)

            if response.status != 200:
                error = f"HTTP {response.status}"
                logger.error(error)
                result["error"] = error
                results.append(result)
                continue

            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            last_logged_percent = 0
            last_logged_bytes = 0
            chunk_size = 8192

            with open(output_path, "wb") as f:
                for chunk in response.stream(chunk_size):
                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        if percent >= last_logged_percent + 5:
                            logger.info(
                                f"Progress: {percent}% ({downloaded:,} / {total_size:,} bytes)"
                            )
                            last_logged_percent = percent

                    elif downloaded - last_logged_bytes > 1_000_000:
                        logger.info(f"Progress: {downloaded:,} bytes downloaded...")
                        last_logged_bytes = downloaded

            logger.info(f"Completed: {downloaded:,} bytes → {output_path}")
            result["path"] = str(output_path)
            result["size"] = downloaded
            response.release_conn()

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
    parser = argparse.ArgumentParser(description="Download files using urllib3")
    parser.add_argument("urls", nargs="+", type=str, help="URLs to download")
    parser.add_argument(
        "-d", "--output_directory", type=str, default=None, help="Save directory"
    )
    parser.add_argument(
        "-f", "--output_filename", type=str, default=None, help="Custom output filename"
    )
    parser.add_argument(
        "--user_agent", type=str, default=None, help="Custom User-Agent"
    )

    args = parser.parse_args()

    download(
        args.urls,
        args.output_directory,
        args.output_filename,
        args.user_agent,
    )
