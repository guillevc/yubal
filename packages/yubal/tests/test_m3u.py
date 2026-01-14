"""Tests for M3U playlist generation utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from yubal.models.domain import TrackMetadata, VideoType
from yubal.utils.m3u import generate_m3u, write_m3u, write_playlist_cover


@pytest.fixture
def sample_track() -> TrackMetadata:
    """Create a sample track for testing."""
    return TrackMetadata(
        omv_video_id="omv123",
        atv_video_id="atv123",
        title="Airbag",
        artists=["Radiohead"],
        album="OK Computer",
        album_artists=["Radiohead"],
        track_number=1,
        total_tracks=12,
        year="1997",
        cover_url="https://example.com/cover.jpg",
        video_type=VideoType.ATV,
    )


@pytest.fixture
def sample_track_multiple_artists() -> TrackMetadata:
    """Create a sample track with multiple artists."""
    return TrackMetadata(
        omv_video_id="omv456",
        atv_video_id="atv456",
        title="Sparks",
        artists=["Coldplay", "Guest Artist"],
        album="Parachutes",
        album_artists=["Coldplay"],
        track_number=3,
        total_tracks=10,
        year="2000",
        cover_url="https://example.com/cover2.jpg",
        video_type=VideoType.ATV,
    )


class TestGenerateM3U:
    """Tests for generate_m3u function."""

    def test_generates_valid_m3u_header(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should generate M3U content with proper header."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        content = generate_m3u([(sample_track, track_path)], m3u_path)

        assert content.startswith("#EXTM3U\n")

    def test_generates_extinf_lines(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should generate EXTINF lines with duration and display name."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        content = generate_m3u([(sample_track, track_path)], m3u_path)

        assert "#EXTINF:-1,Radiohead - Airbag" in content

    def test_uses_relative_paths(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should use paths relative to M3U file location."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        content = generate_m3u([(sample_track, track_path)], m3u_path)

        # Path should be relative and go up from Playlists to find Radiohead
        assert "../Radiohead/1997 - OK Computer/01 - Airbag.opus" in content

    def test_handles_multiple_tracks(
        self,
        sample_track: TrackMetadata,
        sample_track_multiple_artists: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Should handle multiple tracks in correct order."""
        track1_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        track2_path = tmp_path / "Coldplay" / "2000 - Parachutes" / "03 - Sparks.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        tracks = [
            (sample_track, track1_path),
            (sample_track_multiple_artists, track2_path),
        ]
        content = generate_m3u(tracks, m3u_path)

        lines = content.strip().split("\n")
        # Header + 2 tracks * 2 lines each (EXTINF + path)
        assert len(lines) == 5

        # Verify order
        assert lines[0] == "#EXTM3U"
        assert lines[1] == "#EXTINF:-1,Radiohead - Airbag"
        assert "../Radiohead/" in lines[2]
        assert lines[3] == "#EXTINF:-1,Coldplay; Guest Artist - Sparks"
        assert "../Coldplay/" in lines[4]

    def test_multiple_artists_joined_with_semicolon(
        self, sample_track_multiple_artists: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should join multiple artists with semicolon."""
        track_path = tmp_path / "Coldplay" / "2000 - Parachutes" / "03 - Sparks.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        content = generate_m3u([(sample_track_multiple_artists, track_path)], m3u_path)

        assert "#EXTINF:-1,Coldplay; Guest Artist - Sparks" in content

    def test_empty_tracks_list(self, tmp_path: Path) -> None:
        """Should generate valid M3U with only header for empty track list."""
        m3u_path = tmp_path / "Playlists" / "Empty.m3u"

        content = generate_m3u([], m3u_path)

        assert content == "#EXTM3U\n"

    def test_content_ends_with_newline(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should ensure content ends with a trailing newline."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        m3u_path = tmp_path / "Playlists" / "My Playlist.m3u"

        content = generate_m3u([(sample_track, track_path)], m3u_path)

        assert content.endswith("\n")


class TestWriteM3U:
    """Tests for write_m3u function."""

    def test_creates_playlists_directory(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should create Playlists directory if it doesn't exist."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        assert (tmp_path / "Playlists").exists()
        assert (tmp_path / "Playlists").is_dir()

    def test_writes_m3u_file(self, sample_track: TrackMetadata, tmp_path: Path) -> None:
        """Should write M3U file with correct content."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        assert m3u_path.exists()
        content = m3u_path.read_text(encoding="utf-8")
        assert content.startswith("#EXTM3U\n")

    def test_returns_correct_path(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should return the path to the written M3U file."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        assert m3u_path == tmp_path / "Playlists" / "My Favorites.m3u"

    def test_sanitizes_playlist_name(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should sanitize playlist name for safe filename."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        # Name with invalid characters
        m3u_path = write_m3u(
            tmp_path, "My/Favorites: Best<Songs>", [(sample_track, track_path)]
        )

        assert m3u_path.exists()
        # Should not contain invalid characters
        assert "/" not in m3u_path.name
        assert ":" not in m3u_path.name
        assert "<" not in m3u_path.name
        assert ">" not in m3u_path.name

    def test_handles_empty_playlist_name(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should use fallback name for empty playlist name."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(tmp_path, "", [(sample_track, track_path)])

        assert m3u_path.name == "Untitled Playlist.m3u"

    def test_handles_unicode_playlist_name(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should handle unicode characters in playlist name."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(
            tmp_path, "Musique Francaise", [(sample_track, track_path)]
        )

        assert m3u_path.exists()
        # Should create a valid file

    def test_overwrites_existing_file(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should overwrite existing M3U file."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        playlists_dir = tmp_path / "Playlists"
        playlists_dir.mkdir()
        existing_file = playlists_dir / "My Favorites.m3u"
        existing_file.write_text("old content")

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        content = m3u_path.read_text(encoding="utf-8")
        assert content != "old content"
        assert content.startswith("#EXTM3U\n")

    def test_writes_utf8_encoded_file(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should write file with UTF-8 encoding."""
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        # Should be readable as UTF-8
        content = m3u_path.read_text(encoding="utf-8")
        assert "#EXTM3U" in content

    def test_relative_paths_go_up_from_playlists(
        self, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should generate relative paths that go up from Playlists directory."""
        # Create the actual track path structure
        track_dir = tmp_path / "Radiohead" / "1997 - OK Computer"
        track_dir.mkdir(parents=True)
        track_path = track_dir / "01 - Airbag.opus"
        track_path.touch()

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])

        content = m3u_path.read_text(encoding="utf-8")
        # The relative path should go up one directory (from Playlists)
        assert "../Radiohead/1997 - OK Computer/01 - Airbag.opus" in content


class TestWritePlaylistCover:
    """Tests for write_playlist_cover function."""

    def test_returns_none_when_no_cover_url(self, tmp_path: Path) -> None:
        """Should return None when cover_url is None."""
        result = write_playlist_cover(tmp_path, "My Playlist", None)

        assert result is None

    def test_returns_none_when_empty_cover_url(self, tmp_path: Path) -> None:
        """Should return None when cover_url is empty string."""
        result = write_playlist_cover(tmp_path, "My Playlist", "")

        assert result is None

    @patch("yubal.utils.m3u.fetch_cover")
    def test_returns_none_when_fetch_fails(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should return None when fetch_cover returns None."""
        mock_fetch.return_value = None

        result = write_playlist_cover(
            tmp_path, "My Playlist", "https://example.com/cover.jpg"
        )

        assert result is None
        mock_fetch.assert_called_once_with("https://example.com/cover.jpg")

    @patch("yubal.utils.m3u.fetch_cover")
    def test_creates_playlists_directory(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should create Playlists directory if it doesn't exist."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"  # JPEG magic bytes

        write_playlist_cover(tmp_path, "My Playlist", "https://example.com/cover.jpg")

        assert (tmp_path / "Playlists").exists()
        assert (tmp_path / "Playlists").is_dir()

    @patch("yubal.utils.m3u.fetch_cover")
    def test_writes_cover_file(self, mock_fetch: MagicMock, tmp_path: Path) -> None:
        """Should write cover image as JPEG sidecar file."""
        cover_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        mock_fetch.return_value = cover_bytes

        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.read_bytes() == cover_bytes

    @patch("yubal.utils.m3u.fetch_cover")
    def test_returns_correct_path(self, mock_fetch: MagicMock, tmp_path: Path) -> None:
        """Should return the path to the written cover file."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", "https://example.com/cover.jpg"
        )

        assert cover_path == tmp_path / "Playlists" / "My Favorites.jpg"

    @patch("yubal.utils.m3u.fetch_cover")
    def test_sanitizes_playlist_name(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should sanitize playlist name for safe filename."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(
            tmp_path, "My/Favorites: Best<Songs>", "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert cover_path.exists()
        # Should not contain invalid characters
        assert "/" not in cover_path.name
        assert ":" not in cover_path.name
        assert "<" not in cover_path.name
        assert ">" not in cover_path.name

    @patch("yubal.utils.m3u.fetch_cover")
    def test_handles_empty_playlist_name(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should use fallback name for empty playlist name."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(tmp_path, "", "https://example.com/cover.jpg")

        assert cover_path is not None
        assert cover_path.name == "Untitled Playlist.jpg"

    @patch("yubal.utils.m3u.fetch_cover")
    def test_sidecar_matches_m3u_name(
        self, mock_fetch: MagicMock, sample_track: TrackMetadata, tmp_path: Path
    ) -> None:
        """Should create cover with same base name as M3U file."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"

        m3u_path = write_m3u(tmp_path, "My Favorites", [(sample_track, track_path)])
        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert m3u_path.stem == cover_path.stem  # Same base name
        assert m3u_path.suffix == ".m3u"
        assert cover_path.suffix == ".jpg"
