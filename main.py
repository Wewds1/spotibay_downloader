"""Export matching authorized local audio from a Spotify playlist to MP3."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import spotipy

from audio_processor import export_mp3, match_tracks, sanitize_filename, scan_audio
from spotify_client import create_spotify_client, get_playlist, parse_playlist_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match a Spotify playlist to your authorized local audio files and export MP3s.")
    parser.add_argument("playlist", help="Spotify playlist URL, URI, or ID")
    parser.add_argument("--source", type=Path, default=Path("downloads/source"), help="Audio source folder (default: downloads/source)")
    parser.add_argument("--output", type=Path, default=Path("downloads/output"), help="MP3 output folder (default: downloads/output)")
    parser.add_argument("--threshold", type=float, default=85, help="Minimum match confidence, 0–100 (default: 85)")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output files")
    parser.add_argument("--deduplicate", action=argparse.BooleanOptionalAction, default=True,
                        help="Use each source file at most once (default: enabled; use --no-deduplicate to disable)")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    if not 0 <= args.threshold <= 100:
        logging.error("--threshold must be between 0 and 100.")
        return 2
    try:
        playlist_id = parse_playlist_id(args.playlist)
        sp = create_spotify_client()
        playlist_name, tracks = get_playlist(sp, playlist_id)
        logging.info("Playlist: %s (%d accessible tracks)", playlist_name, len(tracks))
        files = scan_audio(args.source)
        logging.info("Found %d supported audio files in %s", len(files), args.source)
        matches = match_tracks(tracks, files, args.threshold, args.deduplicate)
    except (ValueError, RuntimeError, spotipy.SpotifyException) as exc:
        logging.error("%s", exc)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    exported = 0
    for track, source, score in matches:
        artists = track.get("artist") or "Unknown Artist"
        title = track.get("title") or "Unknown Title"
        label = f"{track.get('position', 0):03d} - {artists} - {title}"
        destination = args.output / (sanitize_filename(label) + ".mp3")
        if source is None:
            logging.info("MISS  %s - %s (best confidence %.1f%%)", artists, title, score)
            missing.append(f"{track.get('position', ''):>3} - {artists} - {title}")
            continue
        logging.info("MATCH %s - %s <= %s (%.1f%%)", artists, title, source.path.name, score)
        try:
            export_mp3(source.path, destination, track, overwrite=args.overwrite)
            exported += 1
        except (OSError, RuntimeError) as exc:
            logging.error("Could not export %s: %s", title, exc)
            missing.append(f"{track.get('position', ''):>3} - {artists} - {title} (export failed: {exc})")
    report = args.output / "missing_tracks.txt"
    report.write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
    logging.info("Export complete: %d exported, %d missing or failed. Report: %s", exported, len(missing), report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
