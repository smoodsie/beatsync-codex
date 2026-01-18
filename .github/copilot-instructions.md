# Beatport Playlist Scraper - AI Agent Instructions

## Project Overview
A Python utility that scrapes Beatport playlist pages and extracts normalized track metadata into JSON. The scraper handles multiple JSON extraction sources from the HTML page and normalizes inconsistent field names across different data structures.

## Architecture & Data Flow

### Core Pipeline
1. **Fetch HTML** (`fetch_html`): Downloads page with Mozilla user agent (required to bypass Beatport bot detection)
2. **Extract JSON blobs** (`extract_script_json`): Parses three JSON sources:
   - `__NEXT_DATA__` script tag (Next.js app state)
   - `window.__PRELOADED_STATE__` and `window.__INITIAL_STATE__` globals
   - `data-track` HTML attributes with escaped JSON
3. **Extract tracks** (`extract_tracks_from_data`): Depth-first traversal of nested JSON structures, identifying track objects
4. **Normalize** (`normalize_track`): Maps inconsistent field names to standard output schema
5. **Deduplicate** (`build_playlist_data`): Removes duplicates using song/artist/label tuple

### Field Mapping Strategy
The scraper uses key sets (`TRACK_NAME_KEYS`, `ARTIST_KEYS`, etc.) to handle multiple field name variants from different Beatport API versions. When adding support for new Beatport response formats, add keys to these sets rather than creating format-specific code.

## Key Code Patterns

### Flexible Field Access
```python
TRACK_NAME_KEYS = {"name", "title", "track_name", "trackName"}
find_first(track, TRACK_NAME_KEYS)  # Returns first matching key or None
```
This pattern accommodates API inconsistencies without conditional chains.

### Nested Data Traversal
`extract_tracks_from_data()` uses a stack-based DFS, not recursion, to avoid stack overflow on deeply nested responses. When hunting for tracks in new JSON structures, extend `TRACK_NAME_KEYS` detection logic in `is_track_dict()`.

### Normalization Functions
Each field type has a `normalize_*()` function handling lists, dicts, or strings. For example, `normalize_artist_list()` extracts names from list-of-objects or flattens single strings. Follow this pattern when adding new fields.

## Common Tasks

### Adding Support for New Track Field
1. Add key variant to appropriate `*_KEYS` set
2. Call `find_first()` to retrieve value
3. Create/update `normalize_*()` function if special handling needed
4. Return in normalized track dict in `normalize_track()`

### Debugging Scraper Failures
Run with a Beatport playlist URL:
```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/..." -o debug.json
```
If empty output: Check `extract_script_json()` regex patterns against actual HTML structure (Beatport may have changed HTML).
If incomplete tracks: Add field name variants to appropriate `*_KEYS` or improve `is_track_dict()` detection.

### Test New Beatport Format
The script currently searches three JSON extraction patterns. If Beatport moves data elsewhere (new script ID, different global var), add pattern to `extract_script_json()` regex list.

## Diagnosing Format Changes

When the scraper returns empty results or incomplete tracks, Beatport likely changed their response structure. Debug systematically:

### Step 1: Check JSON Extraction
Add temporary logging to `extract_script_json()` to see what data was found:
```python
blobs = extract_script_json(html)
print(f"Found {len(blobs)} JSON blobs", file=sys.stderr)
print(f"Total keys across blobs: {sum(len(b.keys()) if isinstance(b, dict) else 0 for b in blobs)}", file=sys.stderr)
```
- If `len(blobs) == 0`: Beatport moved the JSON sources. Check actual HTML with browser DevTools (Inspect → Network tab, request the playlist URL, view Response).
- If blobs found but few keys: The script tags may have new IDs or attributes. Search the HTML for patterns like `script` tags or `window.__*` assignments.

### Step 2: Inspect Track Detection
Modify `is_track_dict()` temporarily to understand what's being recognized:
```python
def is_track_dict(data: dict[str, Any]) -> bool:
    keys = set(data.keys())
    # Add logging: print(f"Checking dict with keys: {keys}", file=sys.stderr)
    return bool(keys & TRACK_NAME_KEYS) and (...)
```
If no dicts pass the `is_track_dict()` filter, it means:
- The field names in `*_KEYS` sets no longer match Beatport's response (check with `print(keys)`)
- The detection logic in `is_track_dict()` is too strict (require both artist AND name, but new format has neither)

### Step 3: Locate Track Data in New Format
Once you identify the JSON blob structure:
1. Look for arrays of objects with track metadata (title, artist, BPM, label)
2. Check if there's a `tracks` key (handled specially by `extract_tracks_from_data`)
3. Add new field name variants to the relevant `*_KEYS` sets
4. Possibly adjust `is_track_dict()` detection criteria if the new format is fundamentally different

### Step 4: Add New JSON Extraction Pattern
If data is in a new location entirely (not `__NEXT_DATA__`, `__PRELOADED_STATE__`, or `data-track`):
- Add regex pattern to `extract_script_json()` for the new source
- Example: if data moved to `window.__TRACK_CACHE__ = {...}`, add:
  ```python
  r"window\.__TRACK_CACHE__\s*=\s*(\{.*?\})\s*;"
  ```
- Use non-greedy matching (`.*?`) and test regex on sample HTML before committing

## Error Scenarios & Solutions

### Network Errors
**Problem**: `URLError: [Errno -2] Name or service not known` or timeout
- **Cause**: Network connectivity issue or Beatport domain unreachable
- **Solution**: 
  - Verify URL is valid: `https://www.beatport.com/playlists/PLAYLIST-ID`
  - Test connectivity: `curl -I "https://www.beatport.com"`
  - If Beatport is down, retry later or check Beatport status
  - Add retry logic with exponential backoff if calling from automation

### Invalid URL Format
**Problem**: Script runs but returns empty array `[]`
- **Causes**: 
  - Playlist doesn't exist or is private (Beatport requires public playlists)
  - URL is malformed (typo in playlist ID)
  - URL points to a different page type (artist, label, track) instead of a playlist
- **Solution**:
  - Verify the URL works in a browser and shows the playlist
  - Check that URL matches pattern: `https://www.beatport.com/playlists/...`
  - Private playlists won't work; only public playlists expose data
  - Use `-o debug.json` to examine if HTML was fetched correctly (even if empty JSON output)

### Malformed or Missing HTML
**Problem**: `HTTPError: HTTP Error 403` or `HTTP Error 401`
- **Cause**: Bot detection triggered or authentication required
- **Solution**:
  - User-Agent is already set to Mozilla in `fetch_html()` — if still blocked, Beatport may require additional headers
  - Add `Referer: https://www.beatport.com` header if needed
  - Add delay between requests if scraping multiple playlists: `time.sleep(2)`
  - Check if Beatport requires cookies; may need session handling

### Script Tag Not Found
**Problem**: `extract_script_json()` returns empty blobs but HTML file looks fine
- **Cause**: Regex pattern doesn't match actual HTML structure (whitespace, attributes, encoding)
- **Debug approach**:
  - Save HTML to file: `html = fetch_html(url); open('debug.html', 'w').write(html)`
  - Search for `<script` tags manually in the HTML
  - Test regex patterns in Python REPL: `re.search(pattern, html_sample, re.DOTALL)`
  - Adjust regex: escape special chars, handle optional attributes, use `re.IGNORECASE` if needed
  - Common issue: Beatport may add attributes like `data-module="playlist"` before script content

### Zero or Partial Track Results
**Problem**: Output has some tracks but not all, or completely empty
- **Cause 1**: `is_track_dict()` too restrictive (not matching new field names)
  - Add debug: Log which dicts have track-like keys but fail the filter
  - Add missing field name variants to appropriate `*_KEYS`
- **Cause 2**: Tracks are nested deeper than expected
  - Check if `extract_tracks_from_data()` stack-based DFS is visiting all nodes
  - Manually traverse the JSON blob to find where tracks live
  - May need to add special handling in `extract_tracks_from_data()` for new nesting patterns
- **Cause 3**: Some fields are normalized to empty strings and get filtered
  - In `build_playlist_data()`, check if condition `if normalized_track["song_name"]:`
  - If `song_name` is consistently empty, the `TRACK_NAME_KEYS` aren't matching the actual field names

### Deduplication Removing Valid Tracks
**Problem**: Expected N tracks but output has fewer
- **Cause**: Deduplication key `(song_name, artist_name, label_name)` matches when it shouldn't
- **Debug**: Check if normalization is collapsing different tracks into identical output
- **Solution**: May need to include additional fields in dedup key (e.g., BPM, genre) or fix `normalize_*()` functions that are too aggressive

## Output Schema
```json
{
  "song_name": "Track title + mix name",
  "artist_name": "Comma-separated artist list",
  "label_name": "Label or remix artist names",
  "genre": "Genre slug or name",
  "bpm_key": "BPM (e.g., '130 bpm, Fm')",
  "album_art": "Full image URL"
}
```

## Dependencies
- Python 3.9+ (f-strings, type hints, `from __future__ import annotations`)
- Standard library only (no external packages)
- Network access to Beatport
