from pathlib import Path
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL

INPUT_FILE = "downloads/output/youtube_urls.txt"
OUTPUT_DIR = Path("downloads/musics")
RESULTS_PER_SEARCH = 1   # how many results to take per search query


def to_target(line: str):
    """Turn a line from the file into something yt-dlp can download."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith(("http://", "https://")):
        parsed = urlparse(line)
        # A YouTube search page -> convert to a limited search query
        if parsed.path == "/results":
            query = parse_qs(parsed.query).get("search_query", [""])[0]
            return f"ytsearch{RESULTS_PER_SEARCH}:{query}" if query else None
        # Otherwise assume it's a direct video link
        return line

    # Plain text (e.g. "Apekz Haring Araw") -> search for it
    return f"ytsearch{RESULTS_PER_SEARCH}:{line}"


def load_targets(path: str):
    with open(path, encoding="utf-8") as f:
        targets = [to_target(line) for line in f]
    # Remove blanks and duplicates while keeping order
    return list(dict.fromkeys(t for t in targets if t))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = load_targets(INPUT_FILE)
    print(f"Found {len(targets)} item(s) to download.")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(OUTPUT_DIR / "%(title)s.%(ext)s"),
        "noplaylist": True,                 # a watch link with &list=... won't pull the whole playlist
        "ignoreerrors": True,               # skip unavailable links instead of crashing
        "download_archive": str(OUTPUT_DIR / "archive.txt"),  # skip things already downloaded
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "FFmpegMetadata"},      # embeds title/artist tags
        ],
    }

    with YoutubeDL(options) as ydl:
        ydl.download(targets)


if __name__ == "__main__":
    main()