import unittest

from spotify_client import parse_playlist_id


class PlaylistIdTests(unittest.TestCase):
    def test_url_uri_and_raw_id(self):
        self.assertEqual(parse_playlist_id("https://open.spotify.com/playlist/abc123?si=x"), "abc123")
        self.assertEqual(parse_playlist_id("spotify:playlist:abc123"), "abc123")
        self.assertEqual(parse_playlist_id("abc123"), "abc123")

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            parse_playlist_id("not a playlist")


if __name__ == "__main__":
    unittest.main()
