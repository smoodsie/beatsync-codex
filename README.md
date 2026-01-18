# Beatport Playlist Scraper

This script fetches a public Beatport playlist page and extracts track metadata into a JSON array.

## Requirements

- Python 3.9+
- Network access to Beatport

## Usage

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/your-playlist-id"
```

Write output to a file:

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/your-playlist-id" -o playlist.json
```

## Output format

The script prints a JSON array of track objects:

```json
[
  {
    "song_name": "Take Your Places Extended Mix",
    "artist_name": "Westend, SIDEPIECE",
    "label_name": "Westend, SIDEPIECE",
    "genre": "tech_house",
    "bpm_key": "130 bpm, Fm",
    "album_art": "https://..."
  }
]
```
