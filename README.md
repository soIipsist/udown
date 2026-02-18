# udown

A versatile command-line utility responsible for handling downloads of any type.

`udown` can download videos, playlists, files, and batches of URLs using multiple interchangeable backends. Any of the [default downloaders](#supported-downloaders) can be used to download content from a specified URL. Alternatively, you can [create your own](#creating-a-custom-downloader). Everything is tracked in a local **SQLite database** (`downloads.db`), so you can query downloads effortlessly.

## Installation

### Pip (Linux, Windows)

```bash
pip install "udown[all] @ git+https://github.com/soIipsist/udown.git"
```

### Manual installation

```bash
git clone https://github.com/soIipsist/udown.git
python3 -m venv venv
source venv/bin/activate
pip install -e ".[all]"
```

### Enabling command-line completion (optional)

`udown` supports tab-completion via `argcomplete`. To enable it, paste this in your `.bashrc` or `.zshrc` and restart your shell:

```bash)
eval "$(register-python-argcomplete udown)"
```

Verify it works:

```bash)
udown <TAB>
udown download -t <TAB>
udown downloaders -t <TAB>
```

If configured correctly, available subcommands and downloader types will autocomplete.

## Usage

Running `udown` without arguments is the equivalent to `udown download`.

```bash)
udown
```

### Download command

```bash)
udown download
```

The main command for downloading files, videos, playlists, channels, or batches of URLs.

#### Examples

```python)
# List all downloads
udown download (same as running "udown")

# Download a single URL (default action)
udown "https://youtu.be/MvsAesQ-4zA"

# Explicit download command with downloader type
udown download "https://www.youtube.com/playlist?list=PL3A_1s_Z8MQbYIvki-pbcerX8zrF4U8zQ" -t ytdlp_audio

# Download from a text file containing URLs
udown download downloads.txt

# Custom output directory + proxy
udown download "https://example.com/file.jpg" -o ~/Downloads -p http://proxy:8080

# Filter by status or date range
udown download -s completed -sd 2025-01-01 -ed 2025-12-31 -c OR
```

### Downloaders command

Manage and inspect available download backends/types.

```bash)
udown downloaders
```

#### Examples

```python)
# List all available downloader types
udown downloaders

# List all types like ytdlp_video
udown downloaders -t ytdlp_video

# Add a new custom downloader
udown downloaders add -n mycustom -t ytdlp_audio -d downloader_path.json
```

### Options command

View and modify `udown` options.

```bash)
udown options
```

#### Examples

```python)
# List all available options (no UI)
udown options -ui 0

# Set value of an option
udown options set --key "USE_TUI" --value "0"

# Get value of an option
udown options get --key "USE_TUI"

# Reset all options
udown options reset
```

## Configuration via environment variables

`udown` reads many of its behaviors from environment variables. You can set them in your shell profile (`.bashrc`, `.zshrc`, etc.), in a `.env` file, or export them directly before running commands. Check [.default](./src/.default) for the factory/default settings.

| Variable                | Description                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------- |
| `DATABASE_PATH`         | Full path to the SQLite database file that stores downloads and downloaders                 |
| `DOWNLOADER_TYPE`       | Default downloader type to use when not specified on the command line                       |
| `DOWNLOADER_KEYS`       | Comma-separated fields shown when listing downloaders (`udown downloaders list`)            |
| `DOWNLOADER_OP`         | Default filter conjunction for downloader queries (`AND` or `OR`)                           |
| `DOWNLOADER_ACTION`     | Default subcommand for `udown downloaders` (add, delete, list, reset)                       |
| `DOWNLOAD_DIRECTORY`    | Base directory where downloaded files are saved                                             |
| `DOWNLOAD_FILENAME`     | Default filename for batch URL input when using `--file` or similar                         |
| `DOWNLOAD_ACTION`       | Default action for main download commands (e.g. `add`, `start`, `list`)                     |
| `DOWNLOAD_PROXY`        | Default proxy URL passed to downloaders that support it (http:// or socks5://)              |
| `DOWNLOAD_KEYS`         | Comma-separated fields displayed when listing downloads (`udown list`)                      |
| `DOWNLOAD_OP`           | Default filter conjunction for download queries (`AND` or `OR`)                             |
| `YTDLP_FORMAT`          | Default yt-dlp downloader type/preset when a YouTube-style URL is detected                  |
| `YTDLP_OPTIONS_PATH`    | Path to JSON file with custom yt-dlp format / postprocessor options                         |
| `FFMPEG_OPTS`           | Extra flags passed to ffmpeg when merging or post-processing media                          |
| `YTDLP_VIDEO_DIRECTORY` | Default output directory for video downloads (overrides `DOWNLOAD_DIRECTORY` in some cases) |
| `YTDLP_AUDIO_DIRECTORY` | Default output directory for audio-only downloads                                           |
| `USE_TUI`               | Whether to launch the Textual-based interactive TUI (set to `0` or `false` to disable)      |

### Quick examples

```bash
# Use a dedicated data directory and prefer audio downloads
export DATABASE_PATH=~/udown-data/downloads.db
export DOWNLOAD_DIRECTORY=/mnt/downloads
export YTDLP_FORMAT=ytdlp_audio
export YTDLP_AUDIO_DIRECTORY=/mnt/ssd/Music/Youtube

# Minimal listing output
export DOWNLOAD_KEYS=url,download_status,progress
udown list

# Disable TUI for scripting / logs
export USE_TUI=0

# Use a proxy for all downloads
export DOWNLOAD_PROXY="socks5://127.0.0.1:9050"
```

## Supported downloaders

By default, `udown` automatically detects the downloader type from the specified URL. Override with `--downloader_type <type>`.

**Default downloaders**:

- **yt-dlp family** (`ytdlp`, `ytdlp_video`, `ytdlp_audio`, `ytdlp_video_subs`, …)  
  → videos, audio, playlists, channels

- **wget** & **urllib**  
  → simple & reliable direct file downloads

- **transmission**  
  → magnet links & .torrent files

- **selenium**  
  → JavaScript-heavy / login-protected pages

- **selector** / **xpath**  
  → link extraction from pages (batch downloads)

- **Custom**  
  → register any Python callable you want, [see example below](#creating-a-custom-downloader)

### Creating a custom downloader

`udown` lets you extend its functionality by registering your own download backends. A custom downloader is simply a Python function that you point to from the database.

**Important security note**: When non-default module is loaded for the first time, it will show a warning and ask for confirmation.

#### Step 1: Write your downloader function

Create a Python module somewhere in your project (or in a location Python can import). Example file: `downloaders/my_custom.py`

```python
# downloaders/my_custom.py

import os
from pathlib import Path

def download_my_special_site(
    url: str, # url is REQUIRED
    output_directory: str = None,
    output_filename: str = None,
    quality: str = "720p",           # your own argument
    proxy: str = None,
    **kwargs
) -> dict:
    """
    Example custom downloader function.
    Must return a dict (or yield dicts for playlists/batches) with at least:
    - "status": 0 (success) or 1 (error)
    - optionally: "url", "output_filename", "error", "progress", "is_playlist", etc.
    """
    output_dir = Path(output_directory or "downloads")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    final_filename = output_filename or f"custom_{Path(url).name}"
    output_path = output_dir / final_filename

    # ---- Your actual download logic here ----
    # For example: use requests, httpx, yt-dlp with custom options, API call, etc.
    print(f"Downloading {url} → {output_path} (quality={quality})")

    try:
        # Fake success for this example
        # In reality: do the real work and raise exceptions on failure
        with open(output_path, "wb") as f:
            f.write(b"fake downloaded content\n")
        
        return {
            "status": 0,
            "url": url,
            "output_filename": str(output_path.name),
            "progress": 100
        }
    except Exception as e:
        return {
            "status": 1,
            "error": str(e),
            "url": url
        }

```

#### Step 2: Define the downloader

You need to explicitly define the downloader to use it:

```bash)
udown downloaders add \
  --downloader_type some_type \
  --module downloaders.my_custom \
  --downloader_func download_my_special_site \
  --downloader_args "url, output_directory, output_filename, quality, proxy"
```

#### Step 3: Use your custom downloader

Check if it exists:

```bash)
udown downloaders --downloader_type some_type
```

Then you can use it to download:

```bash)
udown download --downloader_type some_type ...
```
