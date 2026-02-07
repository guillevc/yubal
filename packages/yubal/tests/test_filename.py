"""Tests for filename utilities."""

from pathlib import Path

import pytest
from yubal.utils.filename import (
    build_track_path,
    build_unmatched_track_path,
    clean_filename,
    format_playlist_filename,
)


class TestCleanFilename:
    """Tests for clean_filename function."""

    # === Docstring Examples ===

    def test_docstring_example_bjork(self) -> None:
        """Should pass docstring example: Bjork - Joga stays unchanged."""
        assert clean_filename("Bjork - Joga") == "Bjork - Joga"

    def test_docstring_example_acdc(self) -> None:
        """Should pass docstring example: AC/DC becomes ACDC."""
        assert clean_filename("AC/DC") == "ACDC"

    # === Normal Inputs ===

    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            ("Test Song", "Test Song"),
            ("The Beatles", "The Beatles"),
            ("Abbey Road - Remastered", "Abbey Road - Remastered"),
            ("Track01", "Track01"),
            ("2024", "2024"),
            ("Cafe", "Cafe"),
        ],
        ids=[
            "simple_string",
            "artist_name",
            "album_with_hyphen",
            "alphanumeric",
            "year_only",
            "plain_word",
        ],
    )
    def test_preserves_valid_strings(self, input_str: str, expected: str) -> None:
        """Should preserve strings that don't need sanitization."""
        assert clean_filename(input_str) == expected

    # === Unicode Characters (preserved by pathvalidate) ===

    @pytest.mark.parametrize(
        "input_str",
        [
            "Björk",
            "日本語タイトル",
            "방탄소년단",
            "Кино",
            "Café Tacvba",
            "Sigur Rós",
            "Motörhead",
        ],
    )
    def test_preserves_unicode_characters(self, input_str: str) -> None:
        """Should preserve unicode characters in filenames."""
        assert clean_filename(input_str) == input_str

    def test_unicode_with_invalid_chars_mixed(self) -> None:
        """Should preserve unicode while removing invalid characters."""
        result = clean_filename("Björk: Jóga?")
        assert ":" not in result
        assert "?" not in result
        # Unicode letters should be preserved
        assert "ö" in result
        assert "ó" in result

    # === Invalid Filesystem Characters ===

    @pytest.mark.parametrize(
        ("input_str", "invalid_char"),
        [
            ("AC/DC", "/"),
            ("Path\\to\\file", "\\"),
            ("Song: Part 2", ":"),
            ("Song * Remix", "*"),
            ("Why?", "?"),
            ("Song <Remix>", "<"),
            ("Song <Remix>", ">"),
            ('He said "hello"', '"'),
            ("This | That", "|"),
        ],
        ids=[
            "forward_slash",
            "backslash",
            "colon",
            "asterisk",
            "question_mark",
            "less_than",
            "greater_than",
            "double_quote",
            "pipe",
        ],
    )
    def test_removes_invalid_filesystem_characters(
        self, input_str: str, invalid_char: str
    ) -> None:
        """Should remove characters invalid in filenames."""
        result = clean_filename(input_str)
        assert invalid_char not in result

    def test_removes_all_invalid_characters_combined(self) -> None:
        """Should handle all invalid characters in one string."""
        result = clean_filename('A/B:C*D?E<F>G"H|I\\J')
        for char in '/:*?"<>|\\':
            assert char not in result

    def test_string_with_only_invalid_characters(self) -> None:
        """Should handle strings with only invalid characters."""
        result = clean_filename('/:*?"<>|')
        for char in '/:*?"<>|':
            assert char not in result

    # === Edge Cases ===

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert clean_filename("") == ""

    def test_whitespace_only(self) -> None:
        """Should handle whitespace-only strings."""
        result = clean_filename("   ")
        # Whitespace may be stripped or preserved, but must be safe
        for char in '/:*?"<>|':
            assert char not in result

    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            ("A", "A"),
            ("1", "1"),
            ("-", "-"),
            ("_", "_"),
        ],
        ids=["letter", "digit", "hyphen", "underscore"],
    )
    def test_single_character_inputs(self, input_str: str, expected: str) -> None:
        """Should handle single character strings."""
        assert clean_filename(input_str) == expected

    # === Preserved Valid Characters ===

    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            ("Artist - Song", "Artist - Song"),
            ("song_title", "song_title"),
            ("Song (Live)", "Song (Live)"),
            ("Song [Remastered]", "Song [Remastered]"),
            ("Mr. Smith", "Mr. Smith"),
            ("Rock & Roll", "Rock & Roll"),
            ("It's Alive", "It's Alive"),
        ],
        ids=[
            "hyphens",
            "underscores",
            "parentheses",
            "brackets",
            "dots",
            "ampersand",
            "apostrophe",
        ],
    )
    def test_preserves_valid_special_characters(
        self, input_str: str, expected: str
    ) -> None:
        """Should preserve characters that are valid in filenames."""
        assert clean_filename(input_str) == expected

    # === Control Characters ===

    @pytest.mark.parametrize(
        ("input_str", "invalid_char"),
        [
            ("Line1\nLine2", "\n"),
            ("Tab\there", "\t"),
            ("Return\rhere", "\r"),
            ("Null\x00here", "\x00"),
        ],
        ids=["newline", "tab", "carriage_return", "null"],
    )
    def test_removes_control_characters(
        self, input_str: str, invalid_char: str
    ) -> None:
        """Should remove control characters."""
        result = clean_filename(input_str)
        assert invalid_char not in result

    # === Real-World Examples ===

    @pytest.mark.parametrize(
        ("input_str", "preserved_substring"),
        [
            ("Guns N' Roses", "Guns N' Roses"),
            ("Dr. Dre - 2001", "Dr. Dre - 2001"),
            ("AC/DC", "ACDC"),
            ("What's Going On", "What's Going On"),
        ],
        ids=[
            "guns_n_roses",
            "dr_dre_2001",
            "acdc",
            "whats_going_on",
        ],
    )
    def test_real_world_examples_exact(
        self, input_str: str, preserved_substring: str
    ) -> None:
        """Real-world artist and song names produce expected filenames."""
        result = clean_filename(input_str)
        assert preserved_substring in result

    @pytest.mark.parametrize(
        ("input_str", "invalid_char"),
        [
            ("Batman: The Dark Knight Theme", ":"),
            ("Where Is My Mind?", "?"),
            ("N*E*R*D", "*"),
        ],
        ids=[
            "batman_theme",
            "where_is_my_mind",
            "nerd",
        ],
    )
    def test_real_world_examples_removes_invalid(
        self, input_str: str, invalid_char: str
    ) -> None:
        """Real-world names with invalid chars are sanitized."""
        result = clean_filename(input_str)
        assert len(result) > 0
        assert invalid_char not in result


class TestBuildTrackPath:
    """Tests for build_track_path function."""

    # === Docstring Example ===

    def test_docstring_example(self) -> None:
        """Should pass docstring example."""
        result = build_track_path(Path("/music"), "Artist", "2024", "Album", 1, "Song")
        assert result == Path("/music/Artist/2024 - Album/01 - Song")

    # === Normal Inputs ===

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

    def test_build_path_preserves_unicode(self) -> None:
        """Should preserve unicode characters in path components."""
        result = build_track_path(
            base=Path("/music"),
            artist="Björk",
            year="1997",
            album="Homogenic",
            track_number=2,
            title="Jóga",
        )
        assert result == Path("/music/Björk/1997 - Homogenic/02 - Jóga")

    # === Optional Parameters (None values) ===

    def test_build_path_without_track_number(self) -> None:
        """Should handle None track number (no prefix)."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=None,
            title="Song",
        )
        assert result == Path("/music/Artist/2024 - Album/Song")

    def test_build_path_without_year(self) -> None:
        """Should handle None year with 0000 fallback."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year=None,
            album="Album",
            track_number=1,
            title="Song",
        )
        assert result == Path("/music/Artist/0000 - Album/01 - Song")

    def test_build_path_without_year_and_track_number(self) -> None:
        """Should handle both None year and None track number."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year=None,
            album="Album",
            track_number=None,
            title="Song",
        )
        assert result == Path("/music/Artist/0000 - Album/Song")

    # === Empty String Fallbacks ===

    @pytest.mark.parametrize(
        (
            "artist",
            "album",
            "title",
            "expected_artist",
            "expected_album",
            "expected_title",
        ),
        [
            ("", "Album", "Song", "Unknown Artist", "Album", "Song"),
            ("Artist", "", "Song", "Artist", "Unknown Album", "Song"),
            ("Artist", "Album", "", "Artist", "Album", "Unknown Track"),
            ("", "", "", "Unknown Artist", "Unknown Album", "Unknown Track"),
        ],
        ids=[
            "empty_artist",
            "empty_album",
            "empty_title",
            "all_empty",
        ],
    )
    def test_empty_component_fallbacks(
        self,
        artist: str,
        album: str,
        title: str,
        expected_artist: str,
        expected_album: str,
        expected_title: str,
    ) -> None:
        """Should use fallback values for empty strings."""
        result = build_track_path(
            base=Path("/music"),
            artist=artist,
            year="2024",
            album=album,
            track_number=1,
            title=title,
        )
        assert expected_artist in str(result)
        assert expected_album in str(result)
        assert expected_title in str(result)

    # === Track Number Formatting ===

    @pytest.mark.parametrize(
        ("track_number", "expected_prefix"),
        [
            (1, "01 - "),
            (9, "09 - "),
            (10, "10 - "),
            (12, "12 - "),
            (99, "99 - "),
            (100, "100 - "),
        ],
        ids=[
            "single_digit_1",
            "single_digit_9",
            "double_digit_10",
            "double_digit_12",
            "double_digit_99",
            "triple_digit",
        ],
    )
    def test_track_number_formatting(
        self, track_number: int, expected_prefix: str
    ) -> None:
        """Should format track numbers with leading zeros (at least 2 digits)."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=track_number,
            title="Song",
        )
        assert expected_prefix in str(result)

    def test_track_number_zero(self) -> None:
        """Should handle track number 0."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=0,
            title="Song",
        )
        assert "00 - Song" in str(result)

    # === Sanitization of Components ===

    @pytest.mark.parametrize(
        ("artist", "invalid_char"),
        [
            ("AC/DC", "/"),
            ("Artist: Name", ":"),
            ("Artist?", "?"),
        ],
        ids=["slash_in_artist", "colon_in_artist", "question_in_artist"],
    )
    def test_sanitizes_artist(self, artist: str, invalid_char: str) -> None:
        """Should sanitize invalid characters in artist name."""
        result = build_track_path(
            base=Path("/music"),
            artist=artist,
            year="2024",
            album="Album",
            track_number=1,
            title="Song",
        )
        # Check that invalid chars don't appear in non-base parts
        path_after_base = str(result).replace("/music/", "")
        # Count slashes - should only be 2 (for directory separators)
        if invalid_char == "/":
            assert path_after_base.count("/") == 2
        else:
            assert invalid_char not in path_after_base

    @pytest.mark.parametrize(
        ("album", "invalid_char"),
        [
            ("Album: Part 2", ":"),
            ("Album/Disc 1", "/"),
            ("Album?", "?"),
        ],
        ids=["colon_in_album", "slash_in_album", "question_in_album"],
    )
    def test_sanitizes_album(self, album: str, invalid_char: str) -> None:
        """Should sanitize invalid characters in album name."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album=album,
            track_number=1,
            title="Song",
        )
        path_after_base = str(result).replace("/music/", "")
        if invalid_char == "/":
            assert path_after_base.count("/") == 2
        else:
            assert invalid_char not in path_after_base

    @pytest.mark.parametrize(
        ("title", "invalid_char"),
        [
            ("Song: Remix", ":"),
            ("Song <Live>", "<"),
            ("Song?", "?"),
        ],
        ids=["colon_in_title", "angle_bracket_in_title", "question_in_title"],
    )
    def test_sanitizes_title(self, title: str, invalid_char: str) -> None:
        """Should sanitize invalid characters in title."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=1,
            title=title,
        )
        path_after_base = str(result).replace("/music/", "")
        assert invalid_char not in path_after_base

    def test_sanitizes_all_components_together(self) -> None:
        """Should sanitize multiple components with invalid chars."""
        result = build_track_path(
            base=Path("/music"),
            artist="AC/DC",
            year="2024",
            album="Album: Part 2",
            track_number=1,
            title="Song <Remix>",
        )
        path_after_base = str(result).replace("/music/", "")
        # Only directory separators, no other invalid chars
        for char in ':*?"<>|':
            assert char not in path_after_base
        # Should have exactly 2 slashes (directory separators)
        assert path_after_base.count("/") == 2

    # === Base Path Variations ===

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

    def test_build_path_with_absolute_base(self) -> None:
        """Should work with absolute base path."""
        result = build_track_path(
            base=Path("/home/user/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=1,
            title="Song",
        )
        assert result == Path("/home/user/music/Artist/2024 - Album/01 - Song")

    def test_build_path_with_nested_base(self) -> None:
        """Should work with deeply nested base path."""
        result = build_track_path(
            base=Path("/a/b/c/d/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=1,
            title="Song",
        )
        assert result == Path("/a/b/c/d/music/Artist/2024 - Album/01 - Song")

    # === Year Format Variations ===

    @pytest.mark.parametrize(
        ("year", "expected_folder"),
        [
            ("2024", "2024 - Album"),
            ("1999", "1999 - Album"),
            ("2000", "2000 - Album"),
        ],
        ids=["year_2024", "year_1999", "year_2000"],
    )
    def test_year_formatting(self, year: str, expected_folder: str) -> None:
        """Should preserve year string as-is in folder name."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year=year,
            album="Album",
            track_number=1,
            title="Song",
        )
        assert expected_folder in str(result)

    # === Path Structure Verification ===

    def test_path_structure(self) -> None:
        """Should follow convention: base/Artist/YEAR - Album/NN - Title."""
        result = build_track_path(
            base=Path("/music"),
            artist="The Beatles",
            year="1969",
            album="Abbey Road",
            track_number=7,
            title="Here Comes The Sun",
        )
        parts = result.parts
        assert parts[-4] == "music"
        assert parts[-3] == "The Beatles"
        assert parts[-2] == "1969 - Abbey Road"
        assert parts[-1] == "07 - Here Comes The Sun"

    def test_returns_path_object(self) -> None:
        """Should return a Path object, not a string."""
        result = build_track_path(
            base=Path("/music"),
            artist="Artist",
            year="2024",
            album="Album",
            track_number=1,
            title="Song",
        )
        assert isinstance(result, Path)


class TestBuildUnmatchedTrackPath:
    """Tests for build_unmatched_track_path function."""

    # === Docstring Example ===

    def test_docstring_example(self) -> None:
        """Should pass docstring example."""
        result = build_unmatched_track_path(
            Path("/music"), "Wiz Khalifa", "Mercury Retrograde", "-HJ0ZGkdlTk"
        )
        assert result == Path(
            "/music/_Unmatched/Wiz Khalifa - Mercury Retrograde [-HJ0ZGkdlTk]"
        )

    # === Normal Inputs ===

    def test_basic_path_construction(self) -> None:
        """Should build complete path with all components."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="Test Artist",
            title="Test Song",
            video_id="abc123",
        )
        assert result == Path("/music/_Unmatched/Test Artist - Test Song [abc123]")

    def test_build_path_preserves_unicode(self) -> None:
        """Should preserve unicode characters in path components."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="Björk",
            title="Jóga",
            video_id="xyz789",
        )
        assert result == Path("/music/_Unmatched/Björk - Jóga [xyz789]")

    # === Sanitization of Components ===

    @pytest.mark.parametrize(
        ("artist", "invalid_char"),
        [
            ("AC/DC", "/"),
            ("Artist: Name", ":"),
            ("Artist?", "?"),
        ],
        ids=["slash_in_artist", "colon_in_artist", "question_in_artist"],
    )
    def test_sanitizes_artist(self, artist: str, invalid_char: str) -> None:
        """Should sanitize invalid characters in artist name."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist=artist,
            title="Song",
            video_id="abc123",
        )
        # Check that invalid chars don't appear in non-base parts
        path_after_base = str(result).replace("/music/", "")
        if invalid_char == "/":
            # Only the directory separator between _Unmatched and filename
            assert path_after_base.count("/") == 1
        else:
            assert invalid_char not in path_after_base

    @pytest.mark.parametrize(
        ("title", "invalid_char"),
        [
            ("Song: Remix", ":"),
            ("Song <Live>", "<"),
            ("Song?", "?"),
        ],
        ids=["colon_in_title", "angle_bracket_in_title", "question_in_title"],
    )
    def test_sanitizes_title(self, title: str, invalid_char: str) -> None:
        """Should sanitize invalid characters in title."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="Artist",
            title=title,
            video_id="abc123",
        )
        path_after_base = str(result).replace("/music/", "")
        assert invalid_char not in path_after_base

    def test_sanitizes_all_components_together(self) -> None:
        """Should sanitize multiple components with invalid chars."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="AC/DC",
            title="Song <Remix>",
            video_id="abc123",
        )
        path_after_base = str(result).replace("/music/", "")
        # No invalid filesystem chars in the result
        for char in ':*?"<>|':
            assert char not in path_after_base
        # Should have exactly 1 slash (directory separator for _Unmatched/)
        assert path_after_base.count("/") == 1

    # === Empty String Fallbacks ===

    @pytest.mark.parametrize(
        ("artist", "title", "expected_artist", "expected_title"),
        [
            ("", "Song", "Unknown Artist", "Song"),
            ("Artist", "", "Artist", "Unknown Track"),
            ("", "", "Unknown Artist", "Unknown Track"),
        ],
        ids=[
            "empty_artist",
            "empty_title",
            "all_empty",
        ],
    )
    def test_empty_component_fallbacks(
        self,
        artist: str,
        title: str,
        expected_artist: str,
        expected_title: str,
    ) -> None:
        """Should use fallback values for empty strings."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist=artist,
            title=title,
            video_id="abc123",
        )
        assert expected_artist in str(result)
        assert expected_title in str(result)

    # === Path Structure Verification ===

    def test_path_structure(self) -> None:
        """Should follow convention: base/_Unmatched/Artist - Title [videoId]."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="The Beatles",
            title="Here Comes The Sun",
            video_id="dQw4w9WgXcQ",
        )
        parts = result.parts
        assert parts[-3] == "music"
        assert parts[-2] == "_Unmatched"
        assert parts[-1] == "The Beatles - Here Comes The Sun [dQw4w9WgXcQ]"

    # === Return Type ===

    def test_returns_path_object(self) -> None:
        """Should return a Path object, not a string."""
        result = build_unmatched_track_path(
            base=Path("/music"),
            artist="Artist",
            title="Song",
            video_id="abc123",
        )
        assert isinstance(result, Path)


class TestFormatPlaylistFilename:
    """Tests for format_playlist_filename function."""

    def test_appends_last_8_chars_of_id(self) -> None:
        """Should append last 8 characters of playlist ID."""
        result = format_playlist_filename(
            "My Playlist", "PLrAXtmErZgOeiKm4sgNOknGvNjby9effbd"
        )
        assert result == "My Playlist [by9effbd]"

    def test_uses_full_id_when_short(self) -> None:
        """Should use full ID when it's 8 chars or less."""
        result = format_playlist_filename("My Playlist", "abc123")
        assert result == "My Playlist [abc123]"

    def test_exactly_8_chars_uses_full_id(self) -> None:
        """Should use full ID when it's exactly 8 characters."""
        result = format_playlist_filename("My Playlist", "12345678")
        assert result == "My Playlist [12345678]"

    def test_sanitizes_playlist_name(self) -> None:
        """Should sanitize playlist name but preserve ID suffix."""
        result = format_playlist_filename("My/Invalid:Name", "abc12345678")
        assert "[12345678]" in result
        assert "/" not in result
        assert ":" not in result

    def test_empty_name_uses_fallback(self) -> None:
        """Should use fallback name for empty playlist name."""
        result = format_playlist_filename("", "abc12345678")
        assert result == "Untitled Playlist [12345678]"
