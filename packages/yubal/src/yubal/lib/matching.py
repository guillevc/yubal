"""String matching utilities for title and artist comparison.

This module provides fuzzy matching functions used to compare track titles
and artist names when matching playlist tracks to album tracks or validating
search results.

All fuzzy matching logic is encapsulated here - consumers should use the
high-level result types (TitleMatchResult, ArtistMatchResult) rather than
working with raw similarity scores and thresholds directly.
"""

import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from yubal.models.ytmusic import AlbumTrack, Artist, SearchResult

logger = logging.getLogger(__name__)

# ============================================================================
# PRIVATE CONSTANTS - Thresholds and configuration (not exported)
# ============================================================================

# Fuzzy matching thresholds for album search results (scale 0-100)
_ALBUM_SEARCH_TITLE_THRESHOLD = 70  # Minimum similarity for album search results
_ALBUM_SEARCH_ARTIST_THRESHOLD = 70  # Minimum similarity for artist matching

# Thresholds for track-to-album matching (scale 0-100)
_FUZZY_MATCH_HIGH_CONFIDENCE = 80  # Auto-accept threshold
_FUZZY_MATCH_LOW_CONFIDENCE = 50  # Minimum acceptable threshold

# Common video suffixes to strip when comparing titles (case-insensitive)
# These are added by YouTube for music videos but aren't part of the actual song title
_VIDEO_SUFFIXES = (
    "(official video)",
    "(official music video)",
    "(official audio)",
    "(official lyric video)",
    "(official visualizer)",
    "(music video)",
    "(lyric video)",
    "(lyrics)",
    "(visualizer)",
    "(audio)",
    "(video)",
)


# ============================================================================
# RESULT DATACLASSES - Encapsulate match results with context
# ============================================================================


@dataclass(frozen=True)
class TitleMatchResult:
    """Result of comparing two track titles.

    Attributes:
        similarity: Full title similarity score (0-100).
        base_similarity: Base title similarity (without parenthetical content).
        is_good_match: Whether the match exceeds the title threshold.
        is_base_match: Whether base titles match even if full titles don't.
        target_normalized: Normalized target title.
        candidate_normalized: Normalized candidate title.
    """

    similarity: float
    base_similarity: float
    is_good_match: bool
    is_base_match: bool
    target_normalized: str
    candidate_normalized: str


@dataclass(frozen=True)
class ArtistMatchResult:
    """Result of comparing artist sets.

    Attributes:
        best_score: Highest similarity score among all artist pairs.
        is_good_match: Whether any artist pair exceeds the threshold.
        target_artists: Normalized target artist names.
        candidate_artists: Normalized candidate artist names.
    """

    best_score: float
    is_good_match: bool
    target_artists: frozenset[str]
    candidate_artists: frozenset[str]


@dataclass(frozen=True)
class AlbumSearchMatch:
    """Result of matching a track to an album search result.

    Attributes:
        album_id: ID of the matched album.
        atv_video_id: Audio Track Video ID if available.
        title_match: Details about the title match.
        artist_match: Details about the artist match.
    """

    album_id: str
    atv_video_id: str | None
    title_match: TitleMatchResult
    artist_match: ArtistMatchResult


@dataclass(frozen=True)
class FuzzyTrackMatch:
    """Result of fuzzy matching a track title to album tracks.

    Attributes:
        matched_track: The matched album track.
        score: Similarity score (0-100).
        is_high_confidence: Whether match exceeds high confidence threshold.
        is_acceptable: Whether match exceeds minimum acceptable threshold.
    """

    matched_track: AlbumTrack
    score: float
    is_high_confidence: bool
    is_acceptable: bool


# ============================================================================
# PUBLIC API - High-level matching functions
# ============================================================================


def normalize_title(title: str) -> str:
    """Normalize a title by stripping common video suffixes.

    OMV tracks often have suffixes like "(Official Video)" that don't appear
    in the canonical track name. This function strips those for comparison.

    Args:
        title: Original track title.

    Returns:
        Normalized title with video suffixes removed.
    """
    normalized = title.lower().strip()
    for suffix in _VIDEO_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break  # Only strip one suffix
    return normalized


def extract_base_title(title: str) -> str:
    """Extract the base title by removing all parenthetical content.

    This is useful for matching tracks where parenthetical info differs,
    e.g., "Neverender (feat. Tame Impala)" vs "Neverender (Radio Edit)".
    Both have base title "Neverender".

    Args:
        title: Normalized title (lowercase).

    Returns:
        Base title with all parenthetical content removed.
    """
    # Remove all parenthetical content: (feat. X), (Radio Edit), etc.
    base = re.sub(r"\s*\([^)]*\)\s*", " ", title)
    # Also handle square brackets: [Explicit], [Remastered], etc.
    base = re.sub(r"\s*\[[^\]]*\]\s*", " ", base)
    return base.strip()


def match_title(target: str, candidate: str) -> TitleMatchResult:
    """Compare two track titles and return detailed match information.

    Computes both full title similarity and base title similarity (without
    parenthetical content). A match is considered "good" if either the full
    similarity or base similarity exceeds the threshold.

    Args:
        target: The title we're looking for (e.g., from playlist track).
        candidate: The title to compare against (e.g., from search result).

    Returns:
        TitleMatchResult with similarity scores and match quality flags.
    """
    target_normalized = normalize_title(target)
    candidate_normalized = normalize_title(candidate)

    similarity = fuzz.ratio(target_normalized, candidate_normalized)

    # Compute base title similarity
    target_base = extract_base_title(target_normalized)
    candidate_base = extract_base_title(candidate_normalized)
    base_similarity = (
        fuzz.ratio(target_base, candidate_base)
        if target_base and candidate_base
        else similarity
    )

    is_good_match = similarity >= _ALBUM_SEARCH_TITLE_THRESHOLD
    is_base_match = (
        not is_good_match and base_similarity >= _ALBUM_SEARCH_TITLE_THRESHOLD
    )

    return TitleMatchResult(
        similarity=similarity,
        base_similarity=base_similarity,
        is_good_match=is_good_match or is_base_match,
        is_base_match=is_base_match,
        target_normalized=target_normalized,
        candidate_normalized=candidate_normalized,
    )


def _normalize_artists(artists: list[Artist] | set[str]) -> frozenset[str]:
    """Normalize artist collection to lowercase string set."""
    names: set[str] = set()
    for a in artists:
        raw = a if isinstance(a, str) else a.name
        if raw and (name := raw.lower().strip()):
            names.add(name)
    return frozenset(names)


def match_artists(
    target_artists: list[Artist] | set[str], candidate_artists: list[Artist] | set[str]
) -> ArtistMatchResult:
    """Compare two sets of artists and return detailed match information.

    Finds the best fuzzy match between any pair of artists from the two sets.
    Accepts either Artist objects or pre-normalized string sets.

    Args:
        target_artists: Artists from the track we're matching.
        candidate_artists: Artists from the search result or album track.

    Returns:
        ArtistMatchResult with best score and match quality flags.
    """
    target_set = _normalize_artists(target_artists)
    candidate_set = _normalize_artists(candidate_artists)

    best_score = max(
        (fuzz.ratio(t, c) for t in target_set for c in candidate_set),
        default=0.0,
    )

    return ArtistMatchResult(
        best_score=best_score,
        is_good_match=best_score >= _ALBUM_SEARCH_ARTIST_THRESHOLD,
        target_artists=target_set,
        candidate_artists=candidate_set,
    )


def find_best_album_match(
    track_title: str,
    track_artists: list[Artist],
    search_results: list[SearchResult],
    video_type_atv_value: str,
) -> tuple[AlbumSearchMatch | None, bool]:
    """Find the best matching album from search results.

    Iterates through search results to find one with album info that matches
    the target track's title. Returns match details for logging and the
    first acceptable match.

    Note: This function accepts any result - even low-quality matches -
    because having some album info is better than none. Callers should
    log warnings based on the match quality indicators.

    Args:
        track_title: Title of the track to match.
        track_artists: Artists of the track to match.
        search_results: List of search results to search through.
        video_type_atv_value: The string value representing ATV video type.

    Returns:
        Tuple of (match_result, had_results_with_album):
        - (AlbumSearchMatch, True) if a match was found
        - (None, True) if results had albums but none matched
        - (None, False) if no results had album info
    """
    had_results_with_album = False

    for result in search_results:
        if not result.album:
            continue

        had_results_with_album = True

        title_match = match_title(track_title, result.title)
        artist_match = match_artists(track_artists, result.artists)

        # Accept any result with album info - caller decides how to log
        atv_id = result.video_id if result.video_type == video_type_atv_value else None

        return (
            AlbumSearchMatch(
                album_id=result.album.id,
                atv_video_id=atv_id,
                title_match=title_match,
                artist_match=artist_match,
            ),
            had_results_with_album,
        )

    return None, had_results_with_album


def find_track_by_fuzzy_title(
    album_tracks: list[AlbumTrack], title: str
) -> FuzzyTrackMatch | None:
    """Find the best matching album track using fuzzy title matching.

    Uses rapidfuzz's extractOne to find the most similar track title,
    then evaluates whether the match quality is acceptable.

    Note: Returns the best match even if it's below the acceptable threshold,
    with is_acceptable=False. This allows callers to log rejection details.
    Check is_acceptable before using the matched_track.

    Args:
        album_tracks: List of album tracks to search.
        title: Title to match against.

    Returns:
        FuzzyTrackMatch with match details, or None if no candidates exist.
    """
    if not album_tracks:
        return None

    # Build a mapping from title to track for lookup
    candidates: dict[str, AlbumTrack] = {t.title: t for t in album_tracks}

    result = process.extractOne(title, candidates.keys())
    if not result:
        return None

    matched_title, score, _ = result

    is_high = score > _FUZZY_MATCH_HIGH_CONFIDENCE
    is_acceptable = score > _FUZZY_MATCH_LOW_CONFIDENCE

    return FuzzyTrackMatch(
        matched_track=candidates[matched_title],
        score=score,
        is_high_confidence=is_high,
        is_acceptable=is_acceptable,
    )
