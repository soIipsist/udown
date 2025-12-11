import argparse
import os
import subprocess
import urllib3
from urllib.parse import urlparse
from pathlib import Path


def download(
    urls: list, output_directory: str = None, output_filename: str = None
) -> int:
    http = urllib3.PoolManager()
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

    args = vars(parser.parse_args())
    urls = args.get("urls")
    output_directory = args.get("output_directory")

    results = download(urls, output_directory)
