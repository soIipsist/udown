# udown

A versatile, command-line utility responsible for handling downloads of any type. Supports multiple backends (e.g yt-dlp, wget, urllib), with the additional capability of creating your own custom downloaders.

## Installation

### Pip (Linux, Windows)

```bash
pip install git+https://github.com/soIipsist/udown.git
```

### Manual installation

```bash
git clone https://github.com/soIipsist/udown.git
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

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
udown download 

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

# View detailed information about a specific type
udown downloaders -t ytdlp_video

# Add a new custom downloader
udown downloaders add -n mycustom -t ytdlp_audio -d downloader_path.json

```
