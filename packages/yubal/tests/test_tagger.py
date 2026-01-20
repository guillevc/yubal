"""Tests for audio file tagging."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from yubal.models.domain import TrackMetadata, VideoType
from yubal.services.tagger import tag_track


@pytest.fixture
def sample_track() -> TrackMetadata:
    """Create a sample track for testing."""
    return TrackMetadata(
        omv_video_id="omv123",
        atv_video_id="atv456",
        title="Test Song",
        artists=["Artist One", "Artist Two"],
        album="Test Album",
        album_artists=["Album Artist"],
        track_number=5,
        total_tracks=12,
        year="2024",
        cover_url="https://example.com/cover.jpg",
        video_type=VideoType.ATV,
    )


@pytest.fixture
def sample_track_minimal() -> TrackMetadata:
    """Create a minimal track without optional fields."""
    return TrackMetadata(
        omv_video_id="omv123",
        title="Minimal Song",
        artists=["Artist"],
        album="Album",
        album_artists=["Artist"],
        video_type=VideoType.OMV,
    )


class TestTagTrack:
    """Tests for tag_track function."""

    def test_sets_basic_metadata(self, sample_track: TrackMetadata) -> None:
        """Should set all basic metadata fields."""
        mock_audio = MagicMock()

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track)

        assert mock_audio.title == "Test Song"
        assert mock_audio.artist == "Artist One; Artist Two"
        assert mock_audio.album == "Test Album"
        assert mock_audio.albumartist == "Album Artist"
        mock_audio.save.assert_called_once()

    def test_sets_track_number(self, sample_track: TrackMetadata) -> None:
        """Should set track number and total."""
        mock_audio = MagicMock()

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track)

        assert mock_audio.track == 5
        assert mock_audio.tracktotal == 12

    def test_sets_year_as_int(self, sample_track: TrackMetadata) -> None:
        """Should parse year string to int."""
        mock_audio = MagicMock()

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track)

        assert mock_audio.year == 2024

    def test_sets_cover_art(self, sample_track: TrackMetadata) -> None:
        """Should set cover art (MIME type auto-detected by Image)."""
        mock_audio = MagicMock()
        cover_bytes = b"\xff\xd8\xff" + b"fake image data"

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            with patch("yubal.services.tagger.Image") as mock_image:
                tag_track(Path("/fake/path.opus"), sample_track, cover_bytes)

        mock_image.assert_called_once_with(data=cover_bytes)
        assert mock_audio.images == [mock_image.return_value]

    def test_handles_none_year(self, sample_track_minimal: TrackMetadata) -> None:
        """Should handle track without year."""
        mock_audio = MagicMock()
        mock_audio.year = None

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track_minimal)

        # year should not be set (remains None)
        mock_audio.save.assert_called_once()

    def test_handles_none_track_number(
        self, sample_track_minimal: TrackMetadata
    ) -> None:
        """Should handle track without track number."""
        mock_audio = MagicMock()
        mock_audio.track = None
        mock_audio.tracktotal = None

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track_minimal)

        # track/tracktotal should not be set
        mock_audio.save.assert_called_once()

    def test_handles_none_cover(self, sample_track: TrackMetadata) -> None:
        """Should handle track without cover art."""
        mock_audio = MagicMock()

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            tag_track(Path("/fake/path.opus"), sample_track, cover=None)

        # images should not be set
        assert not hasattr(mock_audio, "images") or mock_audio.images != []
        mock_audio.save.assert_called_once()

    def test_handles_invalid_year(self, sample_track: TrackMetadata) -> None:
        """Should handle invalid year string gracefully."""
        mock_audio = MagicMock()
        track = TrackMetadata(
            omv_video_id="omv123",
            title="Song",
            artists=["Artist"],
            album="Album",
            album_artists=["Artist"],
            year="invalid",
            video_type=VideoType.OMV,
        )

        with patch("yubal.services.tagger.MediaFile", return_value=mock_audio):
            # Should not raise
            tag_track(Path("/fake/path.opus"), track)

        mock_audio.save.assert_called_once()
