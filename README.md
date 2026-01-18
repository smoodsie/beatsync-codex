# Beatport Playlist Scraper

This script fetches a public Beatport playlist page and extracts track metadata into a JSON array.

## Requirements

- Python 3.9+
- Network access to Beatport
- (Optional) Selenium + ChromeDriver for browser automation with `--browser` flag

## Installation

```bash
# Standard installation (urllib only)
pip install -r requirements.txt

# With Selenium for browser automation
pip install -r requirements.txt
pip install selenium
```

## Usage

### Basic usage (extracts first ~25 tracks)

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/share/6138312"
```

Write output to a file:

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/share/6138312" -o playlist.json
```

### With browser automation (experimental)

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/share/6138312" --browser -o playlist.json
```

Uses Selenium to load the page with JavaScript, which may help with pagination on some playlists.

### With login (to unlock additional API access)

If you have a Beatport account, you can log in to potentially unlock authenticated API access for better pagination:

```bash
# First, copy .env.example to .env and add your credentials
cp .env.example .env
# Edit .env and add your Beatport email and password
nano .env

# Then run with --login flag
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/share/6138312" --browser --login -o playlist.json
```

The `.env` file is ignored by git for security.

## Output format

JSON array of track objects:

```json
[
  {
    "song_name": "Take Your Places Extended Mix",
    "artist_name": "Westend, SIDEPIECE",
    "label_name": "Westend, SIDEPIECE",
    "genre": "tech_house",
    "bpm_key": "",
    "album_art": "https://..."
  }
]
```

## Pagination Limitation

Beatport playlists with more than ~25 tracks use server-side pagination. The scraper extracts the first page from the initial HTML load. Full playlist extraction requires authenticated API access or interactive browser session.
]
```
