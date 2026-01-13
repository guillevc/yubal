"""Tests for filename utilities."""

from pathlib import Path

from ytmeta.utils.filename import build_track_path, clean_filename


class TestCleanFilename:
    """Tests for clean_filename function."""

    def test_clean_simple_string(self) -> None:
        """Should leave simple strings unchanged."""
        assert clean_filename("Test Song") == "Test Song"

    def test_clean_unicode_to_ascii(self) -> None:
        """Should convert unicode to ASCII equivalents."""
        assert clean_filename("Bjork") == "Bjork"
        # Unidecode converts accented characters
        result = clean_filename("Cafe")
        assert "Cafe" in result or "cafe" in result.lower()

    def test_clean_removes_invalid_characters(self) -> None:
        """Should remove filesystem-invalid characters."""
        # Forward slash
        result = clean_filename("AC/DC")
        assert "/" not in result

        # Colon
        result = clean_filename("Song: Part 2")
        assert ":" not in result

    def test_clean_handles_empty_string(self) -> None:
        """Should handle empty string."""
        assert clean_filename("") == ""

    def test_clean_handles_special_characters(self) -> None:
        """Should handle various special characters."""
        result = clean_filename('Song <with> "quotes" and |pipes|')
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "|" not in result


class TestBuildTrackPath:
    """Tests for build_track_path function."""

    def test_build_full_path(self) -> None:
        """Should build complete path with all components."""
        result = build_track_path(
            base=Path("/music"),
            artist="Test Artist",
            year="2024",
            album="Test Album",
            track_number=5,
            title="Test Song",
        )

        assert result == Path("/music/Test Artist/2024 - Test Album/05 - Test Song")

    def test_build_path_without_track_number(self) -> None:
        """Should handle missing track number."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=None,
            title="Song",
        )

        # Should not have track number prefix
        assert result == Path("/music/Artist/2024 - Album/Song")

    def test_build_path_without_year(self) -> None:
        """Should handle missing year with fallback."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year=None,
            album="Album",
            track_number=1,
            title="Song",
        )

        assert "0000 - Album" in str(result)

    def test_build_path_sanitizes_components(self) -> None:
        """Should sanitize all path components."""
        result = build_track_path(
            base=Path("/music"),
            artist="AC/DC",
            year="2024",
            album="Album: Part 2",
            track_number=1,
            title="Song <Remix>",
        )

        path_str = str(result)
        assert "/" not in path_str.replace("/music/", "").replace("/", "X", 2)
        # The sanitized path should still be usable

    def test_build_path_handles_empty_components(self) -> None:
        """Should provide fallbacks for empty components."""
        result = build_track_path(
            base=Path("/music"),
            artist="",
            year="2024",
            album="",
            track_number=1,
            title="",
        )

        # Should use fallback values
        assert "Unknown Artist" in str(result)
        assert "Unknown Album" in str(result)
        assert "Unknown Track" in str(result)

    def test_build_path_track_number_formatting(self) -> None:
        """Should format track numbers with leading zero."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=3,
            title="Song",
        )

        assert "03 - Song" in str(result)

        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=12,
            title="Song",
        )

        assert "12 - Song" in str(result)

    def test_build_path_with_relative_base(self) -> None:
        """Should work with relative base path."""
        result = build_track_path(
            base=Path("./downloads"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=1,
            title="Song",
        )

        assert str(result).startswith("downloads")
