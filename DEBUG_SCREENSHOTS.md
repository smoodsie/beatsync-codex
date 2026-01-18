# Debug Screenshots Guide

When running the Beatport scraper with the `--browser` flag, debug screenshots are automatically captured and saved to the `debug/` folder.

## Folder Structure

```
debug/
├── YYYYMMDD_HHMMSS/  (one folder per script run)
│   ├── 02_after_navigation.png
│   ├── 03_after_page_load.png
│   ├── 06_scroll_attempt_0.png
│   ├── 07_end_of_scrollable_content.png
│   ├── 08_after_pagination_complete.png
│   └── 09_final_page_state.png
├── YYYYMMDD_HHMMSS/
│   ├── 01_after_login.png
│   ├── 02_after_navigation.png
│   └── ... (etc)
```

Each run creates a timestamped subfolder containing screenshots from key points in the automation.

## What Each Screenshot Shows

- **02_after_navigation**: Page immediately after navigating to the playlist URL
- **03_after_page_load**: After waiting for JavaScript to load
- **04_before_click_button_attempt_X**: Before clicking a pagination button (if found)
- **05_after_click_button_attempt_X**: After clicking a pagination button
- **06_scroll_attempt_X**: During scroll-based pagination attempts (captured every 10 attempts)
- **07_end_of_scrollable_content**: When the end of scrollable content is reached
- **08_after_pagination_complete**: After pagination attempts are finished
- **09_final_page_state**: Final state of the page before extraction
- **01_after_login**: (if using `--login`) After login attempt completes

## Usage

Run with `--browser` flag to enable Selenium and automatic screenshot capture:

```bash
./beatport_playlist_scraper.py "https://www.beatport.com/playlists/share/..." --browser -o output.json
```

Screenshots will be saved to `debug/YYYYMMDD_HHMMSS/` automatically.

## Cleaning Up

To remove all debug screenshots:

```bash
rm -rf debug/
```

Note: The `debug/` folder is in `.gitignore` and will not be committed to git.
