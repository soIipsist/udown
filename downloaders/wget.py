import argparse
import os
import subprocess
import re

PROGRESS_RE = re.compile(r"(\d+)%")


def build_wget_cmd(url, output_directory=None, output_filename=None):
    cmd = ["wget", "--progress=bar:force"]

    if output_filename:
        output_path = (
            os.path.join(output_directory, output_filename)
            if output_directory
            else output_filename
        )
        cmd += ["-O", output_path]
    elif output_directory:
        cmd += ["-P", output_directory]

    print("USING CMD", cmd)
    cmd.append(url)
    return cmd


def download(urls: list, output_directory: str = None, output_filename: str = None):
    results = []

    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        result = {
            "url": url,
            "status": 0,
            "progress": 0,
        }

        cmd = build_wget_cmd(url, output_directory, output_filename)

        proc = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        try:
            for line in proc.stderr:
                line = line.strip()

                match = PROGRESS_RE.search(line)
                if match:
                    percent = int(match.group(1))
                    result["progress"] = percent

                    print(f"{url} → {percent}%")

            proc.wait()

            if proc.returncode != 0:
                result["status"] = 1
                result["error"] = "wget failed"

        except KeyboardInterrupt:
            proc.terminate()
            result["status"] = 1
            result["error"] = "Interrupted"

        results.append(result)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("-d", "--output_directory", type=str, default=None)
    parser.add_argument(
        "-f",
        "--output_filename",
        type=str,
        default=None,
        help="Output filename",
    )

    args = vars(parser.parse_args())

    urls = args.get("urls")
    output_directory = args.get("output_directory")
    output_filename = args.get("output_filename")
    results = download(urls, output_directory, output_filename)
