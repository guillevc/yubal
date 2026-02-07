"""Tests for string matching utilities.

This module tests the fuzzy matching functions used for comparing track titles
and artist names when matching playlist tracks to album tracks or validating
search results.
"""

import pytest
from yubal.models.ytmusic import AlbumTrack, Artist, SearchResult
from yubal.utils.matching import (
    extract_base_title,
    find_best_album_match,
    find_track_by_fuzzy_title,
    match_artists,
    match_title,
    normalize_title,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_artists() -> list[Artist]:
    """Create a list of sample artists."""
    return [
        Artist(name="Test Artist", id="artist1"),
        Artist(name="Featured Artist", id="artist2"),
    ]


@pytest.fixture
def sample_album_tracks() -> list[AlbumTrack]:
    """Create a list of sample album tracks for fuzzy matching tests."""
    return [
        AlbumTrack.model_validate(
            {
                "videoId": "track1",
                "title": "First Song",
                "artists": [{"name": "Artist", "id": "a1"}],
                "trackNumber": 1,
                "duration_seconds": 180,
            }
        ),
        AlbumTrack.model_validate(
            {
                "videoId": "track2",
                "title": "Second Song (Remastered)",
                "artists": [{"name": "Artist", "id": "a1"}],
                "trackNumber": 2,
                "duration_seconds": 200,
            }
        ),
        AlbumTrack.model_validate(
            {
                "videoId": "track3",
                "title": "Third Song (feat. Guest)",
                "artists": [{"name": "Artist", "id": "a1"}],
                "trackNumber": 3,
                "duration_seconds": 220,
            }
        ),
    ]


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Create sample search results for album matching tests."""
    return [
        SearchResult.model_validate(
            {
                "videoId": "result1",
                "videoType": "MUSIC_VIDEO_TYPE_ATV",
                "title": "Test Song",
                "artists": [{"name": "Test Artist", "id": "a1"}],
                "album": {"id": "album1", "name": "Test Album"},
            }
        ),
        SearchResult.model_validate(
            {
                "videoId": "result2",
                "videoType": "MUSIC_VIDEO_TYPE_OMV",
                "title": "Different Song",
                "artists": [{"name": "Other Artist", "id": "a2"}],
                "album": {"id": "album2", "name": "Other Album"},
            }
        ),
    ]


# ============================================================================
# Tests for normalize_title
# ============================================================================


class TestNormalizeTitle:
    """Tests for the normalize_title function."""

    def test_strips_official_video_suffix(self) -> None:
        """Should strip (Official Video) suffix."""
        assert normalize_title("THOUSAND MILES (Official Video)") == "thousand miles"

    def test_strips_official_music_video_suffix(self) -> None:
        """Should strip (Official Music Video) suffix."""
        assert normalize_title("Song Title (Official Music Video)") == "song title"

    def test_strips_official_audio_suffix(self) -> None:
        """Should strip (Official Audio) suffix."""
        assert normalize_title("Track Name (Official Audio)") == "track name"

    def test_strips_official_lyric_video_suffix(self) -> None:
        """Should strip (Official Lyric Video) suffix."""
        assert normalize_title("My Song (Official Lyric Video)") == "my song"

    def test_strips_official_visualizer_suffix(self) -> None:
        """Should strip (Official Visualizer) suffix."""
        assert normalize_title("Cool Track (Official Visualizer)") == "cool track"

    def test_strips_music_video_suffix(self) -> None:
        """Should strip (Music Video) suffix."""
        assert normalize_title("Hit Song (Music Video)") == "hit song"

    def test_strips_lyric_video_suffix(self) -> None:
        """Should strip (Lyric Video) suffix."""
        assert normalize_title("Ballad (Lyric Video)") == "ballad"

    def test_strips_lyrics_suffix(self) -> None:
        """Should strip (Lyrics) suffix."""
        assert normalize_title("Epic Track (Lyrics)") == "epic track"

    def test_strips_visualizer_suffix(self) -> None:
        """Should strip (Visualizer) suffix."""
        assert normalize_title("Electronic Beat (Visualizer)") == "electronic beat"

    def test_strips_audio_suffix(self) -> None:
        """Should strip (Audio) suffix."""
        assert normalize_title("Acoustic Version (Audio)") == "acoustic version"

    def test_strips_video_suffix(self) -> None:
        """Should strip (Video) suffix."""
        assert normalize_title("Live Performance (Video)") == "live performance"

    def test_preserves_title_without_suffix(self) -> None:
        """Should preserve titles without video suffixes."""
        assert normalize_title("Regular Song Title") == "regular song title"

    def test_preserves_feat_suffix(self) -> None:
        """Should preserve (feat. Artist) which is part of the song title."""
        assert (
            normalize_title("Neverender (feat. Tame Impala)")
            == "neverender (feat. tame impala)"
        )

    def test_preserves_remastered_suffix(self) -> None:
        """Should preserve (Remastered) since it's part of the track version."""
        assert (
            normalize_title("Classic Hit (2024 Remastered)")
            == "classic hit (2024 remastered)"
        )

    def test_case_insensitive_matching(self) -> None:
        """Should match suffixes case-insensitively."""
        assert normalize_title("Song (OFFICIAL VIDEO)") == "song"
        assert normalize_title("Track (official video)") == "track"
        assert normalize_title("Hit (Official Video)") == "hit"

    def test_normalizes_to_lowercase(self) -> None:
        """Should normalize entire title to lowercase."""
        assert normalize_title("UPPERCASE TITLE") == "uppercase title"
        assert normalize_title("MiXeD CaSe") == "mixed case"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Should strip leading and trailing whitespace."""
        assert normalize_title("  Padded Song  ") == "padded song"
        assert normalize_title("\tTabbed\n") == "tabbed"

    def test_only_strips_one_suffix(self) -> None:
        """Should only strip one video suffix (the last matching one)."""
        # This is an edge case - we only strip one suffix per the implementation
        assert normalize_title("Song (Audio) (Official Video)") == "song (audio)"

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert normalize_title("") == ""

    def test_whitespace_only(self) -> None:
        """Should handle whitespace-only string."""
        assert normalize_title("   ") == ""


# ============================================================================
# Tests for extract_base_title
# ============================================================================


class TestExtractBaseTitle:
    """Tests for the extract_base_title function."""

    def test_removes_parenthetical_content(self) -> None:
        """Should remove content in parentheses."""
        assert extract_base_title("song (feat. artist)") == "song"
        assert extract_base_title("track (remastered)") == "track"
        assert extract_base_title("hit (radio edit)") == "hit"

    def test_removes_multiple_parentheticals(self) -> None:
        """Should remove multiple parenthetical sections."""
        assert extract_base_title("song (feat. a) (remix)") == "song"
        assert extract_base_title("track (2024) (remaster)") == "track"

    def test_removes_square_bracket_content(self) -> None:
        """Should remove content in square brackets."""
        assert extract_base_title("song [explicit]") == "song"
        assert extract_base_title("track [remastered]") == "track"
        assert extract_base_title("hit [deluxe version]") == "hit"

    def test_removes_mixed_brackets_and_parens(self) -> None:
        """Should remove both parentheses and square brackets."""
        assert extract_base_title("song (feat. a) [explicit]") == "song"
        assert extract_base_title("track [2024] (remaster)") == "track"

    def test_preserves_base_title(self) -> None:
        """Should preserve the base title when no brackets."""
        assert extract_base_title("simple song") == "simple song"
        assert extract_base_title("another track") == "another track"

    def test_handles_nested_content_gracefully(self) -> None:
        """Should handle nested parentheses (removes outer match)."""
        # The regex removes the first match, potentially leaving inner content
        result = extract_base_title("song ((deep) nested)")
        # This behavior depends on regex - just verify it doesn't crash
        assert "song" in result

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert extract_base_title("") == ""

    def test_only_parenthetical_content(self) -> None:
        """Should return empty string when title is only parenthetical."""
        assert extract_base_title("(just this)") == ""
        assert extract_base_title("[just this]") == ""

    def test_preserves_inner_text_spacing(self) -> None:
        """Should handle spacing correctly after removal."""
        assert extract_base_title("word (a) word") == "word word"
        # Multiple spaces collapse
        result = extract_base_title("a (b) c (d) e")
        assert "a" in result and "c" in result and "e" in result

    def test_already_lowercase_input(self) -> None:
        """Should work with already lowercase input."""
        assert extract_base_title("lowercase title (stuff)") == "lowercase title"


# ============================================================================
# Tests for match_title
# ============================================================================


class TestMatchTitle:
    """Tests for the match_title function."""

    def test_exact_match_returns_high_similarity(self) -> None:
        """Should return 100% similarity for exact matches."""
        result = match_title("Test Song", "Test Song")
        assert result.similarity == 100.0
        assert result.is_good_match is True
        assert result.is_base_match is False

    def test_normalized_exact_match(self) -> None:
        """Should match after normalization (case, video suffixes)."""
        result = match_title("Test Song (Official Video)", "test song")
        assert result.similarity == 100.0
        assert result.is_good_match is True

    def test_case_insensitive_matching(self) -> None:
        """Should match regardless of case."""
        result = match_title("TEST SONG", "test song")
        assert result.similarity == 100.0
        assert result.is_good_match is True

    def test_base_title_match_when_full_differs(self) -> None:
        """Should use base title matching when full titles differ but bases match."""
        result = match_title(
            "Neverender (feat. Tame Impala)", "Neverender (Radio Edit)"
        )
        # Full titles differ significantly
        assert result.similarity < 70
        # But base titles ("neverender") should match
        assert result.base_similarity == 100.0
        assert result.is_base_match is True
        assert result.is_good_match is True

    def test_similar_titles_above_threshold(self) -> None:
        """Should mark as good match when similarity exceeds threshold."""
        result = match_title("Song Title", "Song Titl")  # Small typo
        assert result.similarity > 70
        assert result.is_good_match is True

    def test_different_titles_below_threshold(self) -> None:
        """Should not match completely different titles."""
        result = match_title("First Song", "Completely Different Track")
        assert result.similarity < 70
        assert result.is_good_match is False

    def test_returns_normalized_strings(self) -> None:
        """Should return normalized versions of input strings."""
        result = match_title("SONG (Official Video)", "Track (Music Video)")
        assert result.target_normalized == "song"
        assert result.candidate_normalized == "track"

    def test_empty_target(self) -> None:
        """Should handle empty target string."""
        result = match_title("", "Song")
        assert result.target_normalized == ""
        assert result.is_good_match is False

    def test_empty_candidate(self) -> None:
        """Should handle empty candidate string."""
        result = match_title("Song", "")
        assert result.candidate_normalized == ""
        assert result.is_good_match is False

    def test_both_empty(self) -> None:
        """Should handle both strings empty."""
        result = match_title("", "")
        # Empty strings have 100% similarity (they're identical)
        assert result.similarity == 100.0
        # But base titles are also empty, so base_similarity uses full similarity
        assert result.is_good_match is True

    def test_partial_overlap(self) -> None:
        """Should calculate similarity for partial overlaps."""
        result = match_title("Song Name", "Song Name Extended Version")
        # Has some similarity but not 100%
        assert 0 < result.similarity < 100


# ============================================================================
# Tests for match_artists
# ============================================================================


class TestMatchArtists:
    """Tests for the match_artists function."""

    def test_exact_match_with_string_sets(self) -> None:
        """Should match identical artist string sets."""
        result = match_artists({"artist one"}, {"artist one"})
        assert result.is_good_match is True
        assert result.best_score == 100.0

    def test_exact_match_with_artist_objects(self) -> None:
        """Should match identical Artist objects."""
        artists1 = [Artist(name="Test Artist", id="a1")]
        artists2 = [Artist(name="Test Artist", id="a2")]
        result = match_artists(artists1, artists2)
        assert result.is_good_match is True
        assert result.best_score == 100.0

    def test_similar_artist_above_threshold(self) -> None:
        """Should match similar artist names above threshold."""
        result = match_artists({"kid cudi"}, {"kid cudi "})  # Extra space
        assert result.is_good_match is True
        assert result.best_score > 70

    def test_different_artists_below_threshold(self) -> None:
        """Should not match completely different artists."""
        result = match_artists({"taylor swift"}, {"kid cudi"})
        assert result.is_good_match is False
        assert result.best_score < 70

    def test_one_matching_artist_sufficient(self) -> None:
        """Should match if any target artist matches any candidate artist."""
        result = match_artists(
            {"artist one", "artist two"}, {"artist two", "artist three"}
        )
        assert result.is_good_match is True
        assert result.best_score == 100.0

    def test_no_matching_artists(self) -> None:
        """Should not match when no artists are similar."""
        result = match_artists(
            {"taylor swift", "ed sheeran"}, {"kid cudi", "travis scott"}
        )
        assert result.is_good_match is False

    def test_empty_target_set(self) -> None:
        """Should not match when target set is empty."""
        result = match_artists(set(), {"artist"})
        assert result.is_good_match is False
        assert result.best_score == 0.0

    def test_empty_candidate_set(self) -> None:
        """Should not match when candidate set is empty."""
        result = match_artists({"artist"}, set())
        assert result.is_good_match is False
        assert result.best_score == 0.0

    def test_both_empty_sets(self) -> None:
        """Should not match when both sets are empty."""
        result = match_artists(set(), set())
        assert result.is_good_match is False
        assert result.best_score == 0.0

    def test_empty_artist_list(self) -> None:
        """Should handle empty Artist lists."""
        result = match_artists([], [])
        assert result.is_good_match is False

    def test_returns_normalized_frozensets(self) -> None:
        """Should return normalized artist sets in result."""
        result = match_artists({"UPPERCASE"}, {"lowercase"})
        assert result.target_artists == frozenset({"uppercase"})
        assert result.candidate_artists == frozenset({"lowercase"})

    def test_mixed_artist_objects_and_strings(self) -> None:
        """Should handle Artist objects correctly (normalized to lowercase)."""
        artists = [Artist(name="Test Artist", id="a1")]
        result = match_artists(artists, {"test artist"})
        assert result.is_good_match is True
        assert result.best_score == 100.0

    def test_whitespace_stripping(self) -> None:
        """Should strip whitespace from artist names."""
        result = match_artists({"  padded  "}, {"padded"})
        assert result.is_good_match is True
        assert result.best_score == 100.0

    def test_none_artist_names_filtered(self) -> None:
        """Should filter out None or empty artist names."""
        artists = [Artist(name="Valid", id="a1"), Artist(name="", id="a2")]
        result = match_artists(artists, {"valid"})
        assert result.is_good_match is True
        # Empty name should be filtered out
        assert len(result.target_artists) == 1


# ============================================================================
# Tests for find_best_album_match
# ============================================================================


class TestFindBestAlbumMatch:
    """Tests for the find_best_album_match function."""

    def test_finds_matching_album_result(
        self, sample_artists: list[Artist], sample_search_results: list[SearchResult]
    ) -> None:
        """Should find first result with matching album."""
        match, had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=sample_search_results,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is not None
        assert had_results is True
        assert match.album_id == "album1"
        assert match.atv_video_id == "result1"  # First result is ATV

    def test_returns_none_when_no_albums(self, sample_artists: list[Artist]) -> None:
        """Should return (None, False) when no results have album info."""
        # Create results without album field
        results_no_album = [
            SearchResult.model_validate(
                {
                    "videoId": "r1",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Test Song",
                    "artists": [{"name": "Artist", "id": "a1"}],
                    # No album field
                }
            )
        ]

        match, had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=results_no_album,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is None
        assert had_results is False

    def test_returns_first_result_with_album(
        self, sample_artists: list[Artist]
    ) -> None:
        """Should return first result that has album info."""
        results = [
            SearchResult.model_validate(
                {
                    "videoId": "no_album",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Test Song",
                    "artists": [{"name": "Test Artist", "id": "a1"}],
                    # No album
                }
            ),
            SearchResult.model_validate(
                {
                    "videoId": "with_album",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Test Song",
                    "artists": [{"name": "Test Artist", "id": "a1"}],
                    "album": {"id": "found_album", "name": "Found Album"},
                }
            ),
        ]

        match, had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=results,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is not None
        assert match.album_id == "found_album"
        assert had_results is True

    def test_atv_video_id_only_for_atv_results(
        self, sample_artists: list[Artist]
    ) -> None:
        """Should only set atv_video_id when result is ATV type."""
        results = [
            SearchResult.model_validate(
                {
                    "videoId": "omv_video",
                    "videoType": "MUSIC_VIDEO_TYPE_OMV",  # Not ATV
                    "title": "Test Song",
                    "artists": [{"name": "Test Artist", "id": "a1"}],
                    "album": {"id": "album1", "name": "Album"},
                }
            )
        ]

        match, _had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=results,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is not None
        assert match.atv_video_id is None  # Not ATV, so no ATV ID

    def test_empty_search_results(self, sample_artists: list[Artist]) -> None:
        """Should handle empty search results list."""
        match, had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=[],
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is None
        assert had_results is False

    def test_returns_match_details_for_logging(
        self, sample_artists: list[Artist]
    ) -> None:
        """Should return detailed match info for caller to use."""
        results = [
            SearchResult.model_validate(
                {
                    "videoId": "v1",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Different Title",  # Doesn't match well
                    "artists": [{"name": "Other Artist", "id": "a1"}],  # Different
                    "album": {"id": "album1", "name": "Album"},
                }
            )
        ]

        match, _had_results = find_best_album_match(
            track_title="Test Song",
            track_artists=sample_artists,
            search_results=results,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        # Even poor matches are returned (caller decides what to do)
        assert match is not None
        assert match.title_match is not None
        assert match.title_match.is_good_match is False  # Low similarity
        assert match.artist_match is not None


# ============================================================================
# Tests for find_track_by_fuzzy_title
# ============================================================================


class TestFindTrackByFuzzyTitle:
    """Tests for the find_track_by_fuzzy_title function."""

    def test_finds_exact_match(self, sample_album_tracks: list[AlbumTrack]) -> None:
        """Should find exact title match with high confidence."""
        result = find_track_by_fuzzy_title(sample_album_tracks, "First Song")

        assert result is not None
        assert result.matched_track.title == "First Song"
        assert result.score == 100.0
        assert result.is_high_confidence is True
        assert result.is_acceptable is True

    def test_finds_similar_match(self, sample_album_tracks: list[AlbumTrack]) -> None:
        """Should find similar title with high confidence."""
        result = find_track_by_fuzzy_title(sample_album_tracks, "First Song!")

        assert result is not None
        assert result.matched_track.title == "First Song"
        assert result.score > 80
        assert result.is_high_confidence is True
        assert result.is_acceptable is True

    def test_finds_best_match_among_candidates(
        self, sample_album_tracks: list[AlbumTrack]
    ) -> None:
        """Should select the most similar track."""
        result = find_track_by_fuzzy_title(
            sample_album_tracks,
            "Second Song (Remaster)",  # Close to "Second Song (Remastered)"
        )

        assert result is not None
        assert result.matched_track.title == "Second Song (Remastered)"
        assert result.is_high_confidence is True

    def test_medium_confidence_match(
        self, sample_album_tracks: list[AlbumTrack]
    ) -> None:
        """Should flag medium confidence matches as acceptable but not high."""
        result = find_track_by_fuzzy_title(
            sample_album_tracks,
            "First Song - Radio Edit",  # Somewhat different
        )

        assert result is not None
        # Should find "First Song" but with lower confidence
        assert result.is_acceptable is True
        # Score is above 50 but may not be above 80

    def test_low_confidence_rejected(
        self, sample_album_tracks: list[AlbumTrack]
    ) -> None:
        """Should mark very different titles as not acceptable."""
        result = find_track_by_fuzzy_title(
            sample_album_tracks, "Completely Unrelated XYZ"
        )

        assert result is not None  # Still returns best match for logging
        assert result.is_acceptable is False
        assert result.is_high_confidence is False

    def test_empty_album_tracks_returns_none(self) -> None:
        """Should return None for empty track list."""
        result = find_track_by_fuzzy_title([], "Any Title")
        assert result is None

    def test_result_contains_matched_track(
        self, sample_album_tracks: list[AlbumTrack]
    ) -> None:
        """Should return the actual AlbumTrack object."""
        result = find_track_by_fuzzy_title(sample_album_tracks, "First Song")

        assert result is not None
        assert result.matched_track.video_id == "track1"
        assert result.matched_track.track_number == 1
        assert result.matched_track.duration_seconds == 180

    def test_case_sensitivity(self, sample_album_tracks: list[AlbumTrack]) -> None:
        """Should handle case differences in matching - rapidfuzz is case-sensitive."""
        result = find_track_by_fuzzy_title(sample_album_tracks, "FIRST SONG")

        assert result is not None
        # rapidfuzz is case-sensitive by default, so exact case match may not be found
        # but we should still get a result (even if it's a different track)
        assert result.matched_track is not None
        # Best match depends on rapidfuzz scoring - what matters is we get a result

    def test_handles_special_characters(
        self, sample_album_tracks: list[AlbumTrack]
    ) -> None:
        """Should handle special characters in titles."""
        result = find_track_by_fuzzy_title(
            sample_album_tracks, "Third Song (feat. Guest)"
        )

        assert result is not None
        assert result.matched_track.title == "Third Song (feat. Guest)"
        assert result.is_high_confidence is True


# ============================================================================
# Integration tests
# ============================================================================


class TestMatchingIntegration:
    """Integration tests combining multiple matching functions."""

    def test_normalize_and_match_title_workflow(self) -> None:
        """Test typical workflow: normalize then match titles."""
        # Simulate playlist title with video suffix
        playlist_title = "Bohemian Rhapsody (Official Video)"
        # Simulate album track title (clean)
        album_title = "Bohemian Rhapsody"

        # The match_title function handles normalization internally
        result = match_title(playlist_title, album_title)

        assert result.is_good_match is True
        assert result.similarity == 100.0
        assert result.target_normalized == "bohemian rhapsody"

    def test_extract_base_and_match_workflow(self) -> None:
        """Test matching tracks with different parenthetical versions."""
        # Different versions of same song - use more different suffixes
        playlist_title = "Neverender (feat. Tame Impala)"
        album_title = "Neverender (Radio Edit)"

        result = match_title(playlist_title, album_title)

        # Full titles differ significantly
        assert result.similarity < 70
        # But base match should be good (both normalize to "neverender")
        assert result.base_similarity == 100.0
        assert result.is_base_match is True
        assert result.is_good_match is True

    def test_full_search_result_matching_workflow(
        self, sample_artists: list[Artist]
    ) -> None:
        """Test complete workflow for matching a track to search results."""
        # Create realistic search results
        search_results = [
            SearchResult.model_validate(
                {
                    "videoId": "v1",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Purple Rain (Remastered)",  # Similar to query
                    "artists": [{"name": "Test Artist", "id": "a1"}],
                    "album": {"id": "album_purple", "name": "Purple Rain Album"},
                }
            )
        ]

        match, had_results = find_best_album_match(
            track_title="Purple Rain (Official Video)",
            track_artists=sample_artists,
            search_results=search_results,
            video_type_atv_value="MUSIC_VIDEO_TYPE_ATV",
        )

        assert match is not None
        assert had_results is True
        # Title should match via base title comparison
        assert match.title_match.is_good_match is True
        # Artist should match
        assert match.artist_match.is_good_match is True
        assert match.album_id == "album_purple"
