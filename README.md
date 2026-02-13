# udown

A versatile, command-line utility responsible for handling downloads of any type.

`udown` can download videos, playlists, files, and batches of URLs using multiple interchangeable backends (yt-dlp, wget, urllib, Selenium, custom handlers, etc.).  
It also allows you to register your own downloaders and manage them dynamically.

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
