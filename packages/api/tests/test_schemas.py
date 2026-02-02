"""Tests for API schemas."""

import pytest
from pydantic import ValidationError
from yubal_api.schemas.jobs import CreateJobRequest, validate_youtube_music_url


class TestValidateYouTubeMusicUrl:
    """Tests for YouTube Music URL validation."""

    @pytest.mark.parametrize(
        "url",
        [
            # Playlist URLs
            "https://music.youtube.com/playlist?list=OLAK5uy_test123",
            "https://www.youtube.com/playlist?list=PLtest123",
            "https://music.youtube.com/browse/MPREb_test123",
            # Single track URLs
            "https://music.youtube.com/watch?v=Vgpv5PtWsn4",
            "https://www.youtube.com/watch?v=GkTWxDB21cA",
            "https://youtube.com/watch?v=GkTWxDB21cA",
            # URLs with extra params
            "https://music.youtube.com/watch?v=abc123&si=xyz789",
            "https://music.youtube.com/watch?v=abc123&list=PLtest123",
        ],
        ids=[
            "music_youtube_playlist",
            "youtube_playlist",
            "music_youtube_browse",
            "music_youtube_watch",
            "youtube_watch",
            "youtube_watch_no_www",
            "watch_extra_params",
            "watch_with_list",
        ],
    )
    def test_accepts_valid_urls(self, url: str) -> None:
        """Should accept valid YouTube Music URLs."""
        assert validate_youtube_music_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/test",
            "",
            "https://music.youtube.com/",
            "https://music.youtube.com/watch",
        ],
        ids=["random_url", "empty_url", "youtube_homepage", "watch_no_video_id"],
    )
    def test_rejects_invalid_urls(self, url: str) -> None:
        """Should reject invalid URLs."""
        with pytest.raises(ValueError, match="Invalid URL"):
            validate_youtube_music_url(url)

    def test_strips_whitespace(self) -> None:
        """Should strip whitespace from URL."""
        url = "  https://music.youtube.com/watch?v=abc123  "
        assert validate_youtube_music_url(url) == url.strip()


class TestCreateJobRequest:
    """Tests for CreateJobRequest schema."""

    def test_valid_playlist_url(self) -> None:
        """Should accept valid playlist URL."""
        request = CreateJobRequest(
            url="https://music.youtube.com/playlist?list=OLAK5uy_test123"
        )
        assert request.url == "https://music.youtube.com/playlist?list=OLAK5uy_test123"

    def test_valid_single_track_url(self) -> None:
        """Should accept valid single track URL."""
        request = CreateJobRequest(url="https://music.youtube.com/watch?v=Vgpv5PtWsn4")
        assert request.url == "https://music.youtube.com/watch?v=Vgpv5PtWsn4"

    def test_invalid_url_raises_validation_error(self) -> None:
        """Should raise ValidationError for invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(url="https://example.com/test")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("url",)
        assert "Invalid URL" in str(errors[0]["msg"])

    def test_max_items_optional(self) -> None:
        """Should allow max_items to be omitted."""
        request = CreateJobRequest(url="https://music.youtube.com/watch?v=abc123")
        assert request.max_items is None

    @pytest.mark.parametrize(
        ("max_items", "should_pass"),
        [
            (10, True),
            (1, True),
            (10000, True),
            (0, False),
            (10001, False),
        ],
        ids=["valid_10", "valid_min", "valid_max", "invalid_zero", "invalid_over_max"],
    )
    def test_max_items_range(self, max_items: int, should_pass: bool) -> None:
        """Should validate max_items is within 1-10000."""
        if should_pass:
            request = CreateJobRequest(
                url="https://music.youtube.com/watch?v=abc123",
                max_items=max_items,
            )
            assert request.max_items == max_items
        else:
            with pytest.raises(ValidationError):
                CreateJobRequest(
                    url="https://music.youtube.com/watch?v=abc123",
                    max_items=max_items,
                )
