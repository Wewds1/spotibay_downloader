import unittest
from pathlib import Path

from audio_processor import AudioFile, match_tracks, matching_confidence, sanitize_filename


class AudioProcessorTests(unittest.TestCase):
    def test_filename_sanitization(self):
        self.assertEqual(sanitize_filename('A:B/C? "Song".'), "A_B_C_ _Song_")
        self.assertEqual(sanitize_filename("CON"), "_CON")

    def test_metadata_match(self):
        track = {"artist": "The Example", "title": "A Song!"}
        audio = AudioFile(Path("song.mp3"), "The Example", "A Song")
        self.assertGreaterEqual(matching_confidence(track, audio), 95)

    def test_duplicate_handling(self):
        tracks = [{"artist": "A", "title": "One"}, {"artist": "A", "title": "One"}]
        files = [AudioFile(Path("one.mp3"), "A", "One")]
        self.assertEqual(sum(file is not None for _, file, _ in match_tracks(tracks, files, 80, True)), 1)
        self.assertEqual(sum(file is not None for _, file, _ in match_tracks(tracks, files, 80, False)), 2)


if __name__ == "__main__":
    unittest.main()
