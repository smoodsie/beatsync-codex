#!/usr/bin/env python3
"""Scrape a public Beatport playlist page into JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from typing import Any, Iterable
from urllib.request import Request, urlopen


TRACK_NAME_KEYS = {"name", "title", "track_name", "trackName"}
ARTIST_KEYS = {"artists", "artist", "artist_name", "artistName"}
MIX_KEYS = {"mixName", "mix_name", "mix"}
LABEL_KEYS = {"label", "labelName", "label_name"}
GENRE_KEYS = {"genre", "genreName", "primaryGenre"}
IMAGE_KEYS = {"image", "images", "artwork", "album_art", "albumArt"}


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


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

    bpm = track.get("bpm") or track.get("bpm_value") or track.get("tempo")
    key = track.get("key") or track.get("key_name")
    bpm_key_parts = []
    if bpm:
        bpm_key_parts.append(f"{bpm} bpm")
    if key:
        bpm_key_parts.append(str(key))
    bpm_key = ", ".join(bpm_key_parts)

    album_art = normalize_image(find_first(track, IMAGE_KEYS))

    return {
        "song_name": song_name,
        "artist_name": ", ".join(artists),
        "label_name": label_name,
        "genre": genre_name,
        "bpm_key": bpm_key,
        "album_art": album_art,
    }


def build_playlist_data(html: str) -> list[dict[str, str]]:
    blobs = extract_script_json(html)
    tracks: list[dict[str, Any]] = []
    for blob in blobs:
        tracks.extend(extract_tracks_from_data(blob))

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
        help="Optional output file path (defaults to stdout)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html = fetch_html(args.url)
    playlist = build_playlist_data(html)
    payload = json.dumps(playlist, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        print(payload)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
