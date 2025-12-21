import argparse
import os
import subprocess


def download(urls: list, output_directory: str = None, output_filename: str = None):
    results = []

    if isinstance(urls, str):
        urls = [urls]

    for url in urls:
        result = {"url": url, "status": 0}

        try:
            print("Downloading with wget...")

            if output_filename:
                if output_directory:
                    os.makedirs(output_directory, exist_ok=True)
                    output_path = os.path.join(output_directory, output_filename)
                else:
                    output_path = output_filename

                cmd = ["wget", "-O", output_path, url]

            else:
                if output_directory:
                    os.makedirs(output_directory, exist_ok=True)
                    cmd = ["wget", "-P", output_directory, url]
                else:
                    cmd = ["wget", url]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            result["stdout"] = proc.stdout
            result["stderr"] = proc.stderr

        except KeyboardInterrupt as e:
            result["status"] = 1
            result["error"] = str(e)

        except subprocess.CalledProcessError as e:
            result["status"] = 1
            result["error"] = e.stderr or str(e)

        except Exception as e:
            result["status"] = 1
            result["error"] = f"Unexpected: {e}"

        results.append(result)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("-d", "--output_directory", type=str, default=None)

    args = vars(parser.parse_args())

    urls = args.get("urls")
    output_directory = args.get("output_directory")

    results = download(urls, output_directory)
