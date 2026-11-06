"""Local audio discovery, matching, conversion, and MP3 tagging."""

from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TALB, TIT2, TPE1, TRCK
from rapidfuzz.fuzz import ratio

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif", ".wma"}


@dataclass
class AudioFile:
    path: Path
    artist: str
    title: str


def normalize_text(value: str) -> str:
    """Normalize text for tolerant case and punctuation insensitive matching."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def sanitize_filename(value: str) -> str:
    """Remove characters forbidden in Windows filenames and trim unsafe endings."""
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(". ")
    value = re.sub(r"\s+", " ", value)
    if value.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        value = "_" + value
    return value or "Unknown"


def _tag_value(tags: object, keys: tuple[str, ...]) -> str:
    if not tags:
        return ""
    for key in keys:
        value = tags.get(key) if hasattr(tags, "get") else None
        if value:
            if isinstance(value, (list, tuple)):
                value = value[0]
            return str(value)
    return ""


def read_audio_metadata(path: Path) -> AudioFile:
    """Read common artist/title tags, falling back to an Artist - Title filename."""
    artist = title = ""
    try:
        audio = MutagenFile(path, easy=True)
        if audio:
            artist = _tag_value(audio, ("artist", "albumartist"))
            title = _tag_value(audio, ("title",))
    except Exception:
        pass
    stem = path.stem
    if not title:
        if " - " in stem:
            parsed_artist, parsed_title = stem.split(" - ", 1)
            artist = artist or parsed_artist
            title = parsed_title
        else:
            title = stem
    return AudioFile(path=path, artist=artist, title=title)


def scan_audio(source: Path) -> list[AudioFile]:
    """Recursively discover supported audio files in a source directory."""
    if not source.exists():
        return []
    return [read_audio_metadata(p) for p in sorted(source.rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]


def matching_confidence(track: dict, audio: AudioFile) -> float:
    """Score artist and title similarity on a 0–100 scale."""
    artist_score = ratio(normalize_text(track.get("artist", "")), normalize_text(audio.artist))
    title_score = ratio(normalize_text(track.get("title", "")), normalize_text(audio.title))
    return round(0.45 * artist_score + 0.55 * title_score, 1)


def match_tracks(tracks: list[dict], files: list[AudioFile], threshold: float = 85,
                 deduplicate: bool = True) -> list[tuple[dict, AudioFile | None, float]]:
    """Choose each track's best local candidate, optionally consuming files once."""
    used: set[Path] = set()
    results = []
    for track in tracks:
        candidates = sorted(((matching_confidence(track, file), file) for file in files
                             if not deduplicate or file.path not in used),
                            key=lambda pair: pair[0], reverse=True)
        score, candidate = candidates[0] if candidates else (0.0, None)
        if candidate is None or score < threshold:
            results.append((track, None, score))
        else:
            results.append((track, candidate, score))
            if deduplicate:
                used.add(candidate.path)
    return results


def require_ffmpeg() -> str:
    """Return FFmpeg executable path or raise an actionable error."""
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg was not found on PATH. Install FFmpeg before converting non-MP3 files.")
    return executable


def export_mp3(source: Path, destination: Path, track: dict, overwrite: bool = False,
               bitrate: str = "320k") -> None:
    """Copy an MP3 or convert another supported format, then apply ID3 tags."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {destination}")
    if source.suffix.lower() == ".mp3":
        shutil.copy2(source, destination)
    else:
        ffmpeg = require_ffmpeg()
        result = subprocess.run([ffmpeg, "-nostdin", "-y" if overwrite else "-n", "-i", str(source),
                                 "-vn", "-codec:a", "libmp3lame", "-b:a", bitrate, str(destination)],
                                capture_output=True, text=True)
        if result.returncode:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"FFmpeg conversion failed for {source.name}: {result.stderr[-1200:]}")
    tags = ID3()
    if destination.exists():
        try:
            tags.load(destination)
        except Exception:
            # Valid MP3 files often have no ID3 header yet.
            pass
    tags.delall("TIT2"); tags.delall("TPE1"); tags.delall("TALB"); tags.delall("TRCK")
    tags.add(TIT2(encoding=3, text=track.get("title") or "Unknown"))
    tags.add(TPE1(encoding=3, text=track.get("artist") or "Unknown"))
    if track.get("album"):
        tags.add(TALB(encoding=3, text=track["album"]))
    tags.add(TRCK(encoding=3, text=str(track.get("position", ""))))
    tags.save(destination)
