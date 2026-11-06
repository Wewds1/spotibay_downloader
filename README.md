# Spotify Playlist to Local MP3 Library

A command-line tool that reads playlist metadata through the Spotify Web API, matches it to audio files you are authorized to use in a local folder, and copies or converts those files to tagged MP3s. Spotify is used only for metadata. This project does not download streams or source audio from third-party services.

## Prerequisites

- Python 3.11 or newer
- FFmpeg on `PATH` (needed when converting non-MP3 sources)
- A Spotify Developer application and access to the playlist

## Install

From the project directory, create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate`.

Install FFmpeg using your operating system's package manager or the official FFmpeg download page. Confirm it is available with `ffmpeg -version`.

## Spotify setup

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Add `http://127.0.0.1:8888/callback` as a Redirect URI in the app settings and save.
3. Copy `.env.example` to `.env`, then set the app's Client ID and Client Secret. Keep `.env` private; it is ignored by Git.
4. The first run opens Spotify authorization. Sign in as a Spotify user who can access the playlist and approve the requested private and collaborative playlist read scopes. The token is cached locally in `.spotify_token_cache`.

The redirect URI is read from `SPOTIPY_REDIRECT_URI`; it must exactly match the dashboard configuration.

## Run

Put authorized source audio files in `downloads/source/` (subfolders are scanned), then run:

```powershell
python main.py "https://open.spotify.com/playlist/PLAYLIST_ID"
```

Playlist URIs (`spotify:playlist:...`) and raw playlist IDs also work. Example with options:

```powershell
python main.py "spotify:playlist:PLAYLIST_ID" --source "D:\Music\Library" --output "D:\Music\Export" --threshold 88
```

### Arguments

- `--source`: source audio directory; defaults to `downloads/source`
- `--output`: MP3 output directory; defaults to `downloads/output`
- `--threshold`: minimum match score from 0 to 100; defaults to 85
- `--overwrite`: replace an existing output file; by default existing files are not overwritten
- `--deduplicate` / `--no-deduplicate`: use a source file at most once; enabled by default

## Formats and output

Scanned extensions: MP3, FLAC, WAV, M4A, AAC, OGG, OPUS, AIFF/AIF, and WMA. Actual decoding support depends on the FFmpeg build for conversion. Existing MP3 files are copied without audio re-encoding. Other formats convert with `libmp3lame` at 320 kbps.

Output names follow playlist order, for example `001 - Artist - Song Title.mp3`. ID3 title, artist, album (when available), and playlist position are written; artwork is not embedded. `missing_tracks.txt` lists unmatched tracks and export failures.

## Matching

The tool reads artist and title tags using Mutagen, falling back to `Artist - Title` or just the filename when tags are absent. It normalizes case, accents, and punctuation, then combines RapidFuzz artist (45%) and title (55%) similarity. Candidates below the threshold are reported as missing. Each local source file is used once unless `--no-deduplicate` is selected.

## Troubleshooting

- **Missing credentials:** copy `.env.example` to `.env` and fill in all three values.
- **Redirect URI mismatch:** ensure the dashboard URI and `.env` value match exactly, including scheme, host, port, and path.
- **FFmpeg not found:** install FFmpeg and reopen the terminal so its `bin` directory is on `PATH`. MP3-only copy runs do not require conversion.
- **Playlist inaccessible:** use an account with access. Private and collaborative playlists require the respective OAuth scopes; Spotify API visibility and app access rules still apply.
- **Low match confidence:** check local tags or filename format and lower `--threshold` cautiously.
- **Output exists:** use `--overwrite` to replace output files.
- **Rate limits or API errors:** Spotipy retries transient requests. Try again later, and confirm the playlist remains accessible.

Spotify's API provides metadata and playlist access only. It does not grant the right to reproduce or download recordings; supply only local audio files you are authorized to use. Some playlist tracks can be unavailable, region restricted, local entries, or omitted by Spotify, and are skipped safely.

## Development checks

Run unit tests with `python -m unittest discover -s tests`. Check syntax with `python -m compileall .`. Spotify authentication requires configured credentials and is not covered by offline tests.
