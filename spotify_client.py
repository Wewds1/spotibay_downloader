"""Spotify playlist metadata access."""

from __future__ import annotations

import os
import re
from typing import Any

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "playlist-read-private playlist-read-collaborative"


def parse_playlist_id(value: str) -> str:
    """Return a playlist ID from a Spotify URL, URI, or raw ID."""
    value = value.strip()
    if value.startswith("spotify:playlist:"):
        playlist_id = value.rsplit(":", 1)[-1]
    elif "spotify.com/playlist/" in value:
        match = re.search(r"spotify\.com/playlist/([A-Za-z0-9]+)", value)
        if not match:
            raise ValueError("Could not parse a playlist ID from that URL.")
        playlist_id = match.group(1)
    else:
        playlist_id = value
    if not re.fullmatch(r"[A-Za-z0-9]+", playlist_id):
        raise ValueError("Provide a Spotify playlist URL, URI, or playlist ID.")
    return playlist_id


def create_spotify_client() -> spotipy.Spotify:
    """Authenticate with Spotify using credentials in the environment or .env."""
    load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
    missing = [name for name, value in (("SPOTIPY_CLIENT_ID", client_id),
                                         ("SPOTIPY_CLIENT_SECRET", client_secret),
                                         ("SPOTIPY_REDIRECT_URI", redirect_uri)) if not value]
    if missing:
        raise RuntimeError("Missing environment setting(s): " + ", ".join(missing) + ". Copy .env.example to .env and configure it.")
    auth = SpotifyOAuth(client_id=client_id, client_secret=client_secret,
                        redirect_uri=redirect_uri, scope=SCOPES,
                        cache_path=".spotify_token_cache", open_browser=True)
    return spotipy.Spotify(auth_manager=auth, requests_timeout=15, retries=3)


def get_playlist(sp: spotipy.Spotify, playlist_id: str) -> tuple[str, list[dict[str, Any]]]:
    """Fetch playlist name and accessible tracks, following API pagination."""
    playlist = sp.playlist(playlist_id, fields="name")
    name = playlist.get("name") or "Untitled playlist"
    tracks: list[dict[str, Any]] = []
    page = sp.playlist_items(playlist_id, limit=100,
                             fields="items(track(id,name,artists(name),album(name),duration_ms,track_number,is_local,is_playable)),next")
    position = 0
    while page:
        for item in page.get("items", []):
            position += 1
            track = (item or {}).get("track")
            if (not track or track.get("is_local") or not track.get("name")
                    or track.get("is_playable") is False):
                continue
            artists = [a.get("name", "") for a in (track.get("artists") or []) if a and a.get("name")]
            album = track.get("album") or {}
            tracks.append({
                "id": track.get("id"), "title": track.get("name"), "artists": artists,
                "artist": ", ".join(artists), "album": album.get("name") or "",
                "duration_ms": track.get("duration_ms"), "track_number": track.get("track_number"),
                "position": position,
            })
        page = sp.next(page) if page.get("next") else None
    return name, tracks
