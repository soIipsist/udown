import argparse
import os
from pprint import PrettyPrinter
import subprocess
import urllib3
from urllib.parse import urlparse
from pathlib import Path

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


def download(
    urls: list,
    output_directory: str = None,
    output_filename: str = None,
    user_agent: str = None,
    headers: str = None,
) -> int:

    headers = headers or DEFAULT_HEADERS

    if user_agent:
        headers["User-Agent"] = user_agent

    # print("Using headers: ")
    # pp.pprint(headers)

    http = urllib3.PoolManager(headers=headers)
    results = []

    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        result = {"url": url, "status": 0}
        try:
            path = urlparse(url).path

            filename = (
                output_filename
                if output_filename
                else os.path.basename(path) or "filename"
            )

            # Determine output path
            output_dir = Path(output_directory) if output_directory else Path(".")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename

            response = http.request("GET", url, preload_content=False)

            if response.status != 200:
                error = f"Failed to download {url}: HTTP {response.status}"
                print(error)
                result["error"] = error

            with open(output_path, "wb") as f:
                for chunk in response.stream(1024):
                    f.write(chunk)

            print(f"Downloaded: {url} → {output_path}")
            response.release_conn()
        except KeyboardInterrupt as e:
            print("User interrupted the download.")
            result["status"] = 1
            result["error"] = str(e)
        except subprocess.CalledProcessError as e:
            result["status"] = 1
            result["error"] = str(e)
        except Exception as e:
            error = f"Error downloading {url}: {e}"
            print(error)
            result["error"] = error
            result["status"] = 1

        results.append(result)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download files using urllib3")
    parser.add_argument("urls", nargs="+", type=str, help="URLs to download")
    parser.add_argument(
        "-d",
        "--output_directory",
        type=str,
        default=None,
        help="Directory to save downloads",
    )

    parser.add_argument(
        "-f",
        "--output_filename",
        type=str,
        default=None,
        help="Output filename",
    )
    parser.add_argument(
        "--user_agent",
        type=str,
        default=None,
        help="Custom User-Agent header",
    )

    parser.add_argument("--headers", type=str, default=DEFAULT_HEADERS)
    args = parser.parse_args()

    headers = DEFAULT_HEADERS.copy()
    if args.header:
        for h in args.header:
            key, value = h.split(":", 1)
            headers[key.strip()] = value.strip()

    download(
        args.urls,
        args.output_directory,
        args.output_filename,
        args.user_agent,
        headers,
    )
