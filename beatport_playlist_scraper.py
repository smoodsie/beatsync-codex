#!/usr/bin/env python3
"""Scrape a public Beatport playlist page into JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from datetime import datetime
from html import unescape
from typing import Any, Iterable
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


TRACK_NAME_KEYS = {"name", "title", "track_name", "trackName"}
ARTIST_KEYS = {"artists", "artist", "artist_name", "artistName"}
MIX_KEYS = {"mixName", "mix_name", "mix"}
LABEL_KEYS = {"label", "labelName", "label_name"}
GENRE_KEYS = {"genre", "genreName", "primaryGenre"}
IMAGE_KEYS = {"image", "images", "artwork", "album_art", "albumArt"}


def fetch_html(url: str) -> str:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def login_to_beatport(driver: Any) -> bool:
    """Attempt to log in to Beatport using credentials from .env file."""
    email = os.getenv("BEATPORT_EMAIL", "").strip()
    password = os.getenv("BEATPORT_PASSWORD", "").strip()
    
    if not email or not password:
        return False
    
    try:
        import time
        print(f"Attempting to log in to Beatport as {email}...", file=sys.stderr)
        
        # Navigate to login
        driver.get("https://www.beatport.com/account/login/")
        time.sleep(2)
        
        # Find and fill email field
        email_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[placeholder*='email' i], input[name*='email' i]")
        if email_inputs:
            email_inputs[0].send_keys(email)
            print("Entered email", file=sys.stderr)
            time.sleep(1)
        
        # Find and fill password field
        password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password'], input[name*='password' i]")
        if password_inputs:
            password_inputs[0].send_keys(password)
            print("Entered password", file=sys.stderr)
            time.sleep(1)
        
        # Find and click submit button
        submit_buttons = driver.find_elements(By.XPATH, 
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login') or "
            "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]")
        
        if submit_buttons:
            submit_buttons[0].click()
            print("Clicked login button", file=sys.stderr)
            time.sleep(3)
            return True
        
        return False
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        return False


def get_session_cookies(driver: Any) -> dict[str, str]:
    """Extract session cookies from Selenium driver."""
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']
    return cookies


def create_debug_folder() -> str:
    """Create a debug folder with timestamp subfolder. Returns folder path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_path = os.path.join("debug", timestamp)
    os.makedirs(debug_path, exist_ok=True)
    return debug_path


def take_screenshot(driver: Any, debug_folder: str, name: str) -> None:
    """Take a screenshot and save it to the debug folder."""
    if not os.path.exists(debug_folder):
        os.makedirs(debug_folder, exist_ok=True)
    
    screenshot_path = os.path.join(debug_folder, f"{name}.png")
    try:
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved: {screenshot_path}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to save screenshot {name}: {e}", file=sys.stderr)


def fetch_html_with_selenium(url: str, wait_time: int = 15, extract_all: bool = True, use_login: bool = False, enable_debug: bool = False) -> tuple[str, dict[str, str]]:
    """Fetch HTML using Selenium with URL-based pagination. Returns (html, cookies)."""
    if not SELENIUM_AVAILABLE:
        print("Selenium not available. Use: pip install selenium", file=sys.stderr)
        return fetch_html(url), {}
    
    try:
        import time
        
        # Create debug folder only if debug mode is enabled
        debug_folder = create_debug_folder() if enable_debug else None
        if debug_folder:
            print(f"Debug folder: {debug_folder}", file=sys.stderr)
        
        # Use Chrome with headless mode
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0")
        
        driver = webdriver.Chrome(options=options)
        
        try:
            # Try to log in if credentials are available
            if use_login:
                print("Attempting login...", file=sys.stderr)
                login_to_beatport(driver)
                take_screenshot(driver, debug_folder, "01_after_login")
            
            # Collect all page sources with per_page=100 strategy
            all_page_sources = []
            page = 1
            total_tracks = 0
            
            if extract_all:
                print("Fetching playlist pages with page=X&per_page=100 strategy...", file=sys.stderr)
                
                while True:
                    # Build URL with pagination parameters
                    if '?' in url:
                        paginated_url = f"{url}&page={page}&per_page=100"
                    else:
                        paginated_url = f"{url}?page={page}&per_page=100"
                    
                    print(f"Loading page {page} with per_page=100...", file=sys.stderr)
                    driver.get(paginated_url)
                    time.sleep(2)
                    if debug_folder:
                        take_screenshot(driver, debug_folder, f"02_page_{page}")
                    
                    # Wait for page to load
                    try:
                        WebDriverWait(driver, wait_time).until(
                            lambda d: len(d.find_elements(By.TAG_NAME, "script")) > 5
                        )
                    except Exception as e:
                        print(f"Wait timeout on page {page}: {e}. Continuing.", file=sys.stderr)
                    
                    # Count tracks on this page from React state
                    current_tracks = driver.execute_script("""
                        try {
                            const nextData = document.querySelector('script#__NEXT_DATA__');
                            if (nextData && nextData.textContent) {
                                const data = JSON.parse(nextData.textContent);
                                if (data.props?.pageProps?.dehydratedState?.queries) {
                                    const results = data.props.pageProps.dehydratedState.queries[1]?.state?.data?.results || [];
                                    return results.length;
                                }
                            }
                        } catch(e) {}
                        return 0;
                    """)
                    
                    print(f"Page {page}: {current_tracks} tracks", file=sys.stderr)
                    total_tracks += current_tracks
                    all_page_sources.append(driver.page_source)
                    
                    # Stop if we got fewer than 100 tracks (end of playlist)
                    if current_tracks < 100:
                        print(f"Reached end of playlist (page {page})", file=sys.stderr)
                        break
                    
                    page += 1
                    if page > 100:  # Safety limit to prevent infinite loops
                        print("Reached safety limit of 100 pages", file=sys.stderr)
                        break
                
                print(f"Completed pagination: {page} page(s), {total_tracks} total tracks", file=sys.stderr)
                if debug_folder:
                    take_screenshot(driver, debug_folder, "03_pagination_complete")
                
                # Use the first page source (contains all track data with per_page=100)
                page_source = all_page_sources[0] if all_page_sources else ""
            else:
                # Single page load without pagination
                print(f"Navigating to {url}...", file=sys.stderr)
                driver.get(url)
                time.sleep(2)
                if debug_folder:
                    take_screenshot(driver, debug_folder, "02_page_load")
                
                try:
                    WebDriverWait(driver, wait_time).until(
                        lambda d: len(d.find_elements(By.TAG_NAME, "script")) > 5
                    )
                except Exception as e:
                    print(f"Wait timeout: {e}. Continuing.", file=sys.stderr)
                
                page_source = driver.page_source
            
            # Save HTML to debug folder if enabled
            if debug_folder:
                html_debug_path = os.path.join(debug_folder, "page_source.html")
                with open(html_debug_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
            
            # Extract cookies
            cookies = get_session_cookies(driver)
            
            print(f"Retrieved {len(page_source)} bytes of HTML", file=sys.stderr)
            if debug_folder:
                take_screenshot(driver, debug_folder, "04_final")
            
            return page_source, cookies
        finally:
            driver.quit()
    except Exception as e:
        print(f"Selenium error: {e}. Falling back to standard fetch.", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return fetch_html(url), {}


def extract_script_json(html: str) -> list[Any]:
    blobs: list[Any] = []

    next_data_match = re.search(
        r"<script[^>]+id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>",
        html,
        re.DOTALL,
    )
    if next_data_match:
        raw = unescape(next_data_match.group(1)).strip()
        try:
            blobs.append(json.loads(raw))
        except json.JSONDecodeError:
            pass

    state_patterns = [
        r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;",
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;",
    ]
    for pattern in state_patterns:
        for match in re.finditer(pattern, html, re.DOTALL):
            raw = match.group(1)
            try:
                blobs.append(json.loads(raw))
            except json.JSONDecodeError:
                continue

    data_track_matches = re.findall(r"data-track=\"(\{.*?\})\"", html)
    for match in data_track_matches:
        try:
            blobs.append(json.loads(unescape(match)))
        except json.JSONDecodeError:
            continue

    return blobs


def is_track_dict(data: dict[str, Any]) -> bool:
    keys = set(data.keys())
    return bool(keys & TRACK_NAME_KEYS) and (
        bool(keys & ARTIST_KEYS) or bool(keys & MIX_KEYS) or "bpm" in keys
    )


def iter_nested(data: Any) -> Iterable[Any]:
    if isinstance(data, dict):
        for value in data.values():
            yield value
    elif isinstance(data, list):
        for value in data:
            yield value


def extract_tracks_from_data(data: Any) -> list[dict[str, Any]]:
    """Extract track objects from nested data structures."""
    tracks: list[dict[str, Any]] = []
    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if "tracks" in current and isinstance(current["tracks"], list):
                for track in current["tracks"]:
                    if isinstance(track, dict):
                        tracks.append(track)
            if is_track_dict(current):
                tracks.append(current)
        stack.extend(iter_nested(current))
    return tracks


def find_first(data: dict[str, Any], keys: set[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def normalize_artist_list(value: Any) -> list[str]:
    if isinstance(value, list):
        names = []
        for entry in value:
            if isinstance(entry, dict) and "name" in entry:
                names.append(str(entry["name"]))
            elif isinstance(entry, str):
                names.append(entry)
        return names
    if isinstance(value, dict) and "name" in value:
        return [str(value["name"])]
    if isinstance(value, str):
        return [value]
    return []


def normalize_label(value: Any, remixers: list[str]) -> str:
    if isinstance(value, dict) and "name" in value:
        return str(value["name"])
    if isinstance(value, str):
        return value
    if remixers:
        return ", ".join(remixers)
    return ""


def normalize_genre(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("name", "slug"):
            if key in value:
                return str(value[key])
    if isinstance(value, str):
        return value
    return ""


def normalize_image(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("uri", "url"):
            if key in value:
                return str(value[key])
        for entry in value.values():
            if isinstance(entry, str) and entry.startswith("http"):
                return entry
    if isinstance(value, list):
        for entry in value:
            image = normalize_image(entry)
            if image:
                return image
    return ""


def normalize_track(track: dict[str, Any]) -> dict[str, str]:
    title = find_first(track, TRACK_NAME_KEYS) or ""
    mix_name = find_first(track, MIX_KEYS) or ""

    artists = normalize_artist_list(find_first(track, ARTIST_KEYS))
    remixers = normalize_artist_list(track.get("remixers"))

    if isinstance(mix_name, dict) and "name" in mix_name:
        mix_name = mix_name["name"]

    title_parts = [str(title).strip()]
    mix_name_text = str(mix_name).strip()
    if mix_name_text and mix_name_text.lower() not in {"original mix", "original"}:
        title_parts.append(mix_name_text)

    if remixers and not mix_name_text:
        title_parts.append(" ".join([", ".join(remixers), "Remix"]))

    song_name = " ".join(part for part in title_parts if part).strip()

    label_name = normalize_label(find_first(track, LABEL_KEYS), remixers)
    genre_name = normalize_genre(find_first(track, GENRE_KEYS))

    bpm_key = ""

    album_art = normalize_image(find_first(track, IMAGE_KEYS))

    return {
        "song_name": song_name,
        "artist_name": ", ".join(artists),
        "label_name": label_name,
        "genre": genre_name,
        "bpm_key": bpm_key,
        "album_art": album_art,
    }


def extract_playlist_name(html: str) -> str:
    """Extract playlist name from JSON blobs or page title."""
    blobs = extract_script_json(html)
    
    # Search JSON blobs for playlist name
    for blob in blobs:
        stack = [blob]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key in ("name", "title", "playlistName", "playlist_name"):
                    if key in current:
                        value = current[key]
                        if isinstance(value, str) and len(value) > 0:
                            # Check if this looks like a playlist name (not a track name)
                            if "mix" not in value.lower() or len(value) > 15:
                                return value
            stack.extend(iter_nested(current))
    
    # Fallback to page title
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        # Remove common suffixes like "- Beatport"
        title = re.sub(r"\s*[-|]\s*Beatport\s*$", "", title, flags=re.IGNORECASE)
        if title:
            return title
    
    return "playlist"


def build_playlist_data(html: str, cookies: dict[str, str] | None = None, playlist_url: str | None = None) -> list[dict[str, str]]:
    """Extract and normalize track data from HTML."""
    blobs = extract_script_json(html)
    tracks: list[dict[str, Any]] = []
    
    # Extract from HTML
    for blob in blobs:
        tracks.extend(extract_tracks_from_data(blob))
    
    print(f"Extracted {len(tracks)} tracks from HTML", file=sys.stderr)

    # Normalize and deduplicate
    seen = set()
    normalized: list[dict[str, str]] = []
    for track in tracks:
        normalized_track = normalize_track(track)
        key = (
            normalized_track["song_name"],
            normalized_track["artist_name"],
            normalized_track["label_name"],
        )
        if key in seen:
            continue
        seen.add(key)
        if normalized_track["song_name"]:
            normalized.append(normalized_track)
    
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract playlist details from a Beatport playlist page",
    )
    parser.add_argument("url", help="Beatport playlist URL")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output file path (defaults to auto-generated name)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (saves screenshots and HTML to debug folder)",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Log in to Beatport using credentials from .env file (requires BEATPORT_EMAIL and BEATPORT_PASSWORD)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    cookies = {}
    html = ""
    
    # Always use Selenium for browser automation
    if not SELENIUM_AVAILABLE:
        print("Error: Selenium not installed. Install with: pip install selenium", file=sys.stderr)
        print("Also ensure ChromeDriver is in PATH or installed via selenium-manager", file=sys.stderr)
        sys.exit(1)
    
    print("Using Selenium for browser automation...", file=sys.stderr)
    use_login = args.login and (os.getenv("BEATPORT_EMAIL") or os.getenv("BEATPORT_PASSWORD"))
    html, cookies = fetch_html_with_selenium(args.url, use_login=use_login, enable_debug=args.debug)
    print(f"Page loaded with {len(html)} bytes of content", file=sys.stderr)
    if cookies:
        print(f"Captured {len(cookies)} session cookies", file=sys.stderr)
    
    # Build playlist, optionally using API with cookies
    playlist = build_playlist_data(html, cookies=cookies if cookies else None, playlist_url=args.url)
    payload = json.dumps(playlist, indent=2, ensure_ascii=False)
    
    # Determine output file
    output_path = args.output
    if not output_path:
        playlist_name = extract_playlist_name(html)
        # Sanitize filename: remove special chars, replace spaces with underscores
        safe_name = re.sub(r"[^a-zA-Z0-9_\s-]", "", playlist_name)
        safe_name = re.sub(r"\s+", "_", safe_name).strip("_")
        # Append timestamp in DDMMYYYY_HH_MM_SS format
        timestamp = datetime.now().strftime("%d%m%Y_%H_%M_%S")
        output_path = f"{safe_name}_{timestamp}.json"
    
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    
    print(f"Playlist saved to {output_path}", file=sys.stderr)
    print(f"Total tracks extracted: {len(playlist)}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
