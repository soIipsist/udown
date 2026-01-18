import argparse
import os
import subprocess
import re
from utils.logger import setup_logger

logger = setup_logger(name="wget", log_dir="/udown/wget")
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

    cmd.append(url)
    return cmd


def download(urls: list, output_directory: str = None, output_filename: str = None):

    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        cmd = build_wget_cmd(url, output_directory, output_filename)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        try:
            for line in proc.stdout:
                line = line.strip()
                match = PROGRESS_RE.search(line)
                if match:
                    percent = match.group(1)
                    logger.info(percent)
                    yield {"url": url, "status": 0, "progress": f"{percent}%"}

            proc.wait()

            if proc.returncode == 0:
                yield {"url": url, "status": 0, "progress": "100%"}
            else:
                yield {"url": url, "status": 1, "error": "wget failed"}

        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            yield {"url": url, "status": 1, "error": "Interrupted"}

        finally:
            if proc.stdout:
                proc.stdout.close()
            if proc.poll() is None:
                proc.terminate()
                proc.wait()


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
