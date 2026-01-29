import argparse
import os
import subprocess


def download(urls: list, output_directory: str = None):
    results = []

    if output_directory:
        output_directory = os.path.abspath(output_directory)
        os.makedirs(output_directory, exist_ok=True)

    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        cmd = ["transmission-cli", url]

        if output_directory:
            cmd.extend(["-w", output_directory])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        results.append(
            {
                "url": url,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("-d", "--output_directory", type=str, default=None)

    args = vars(parser.parse_args())

    urls = args.get("urls")
    output_directory = args.get("output_directory")
    results = download(urls, output_directory)
