"""Tests for API schemas."""

import pytest
from yubal_api.schemas.jobs import validate_youtube_music_url


class TestValidateYouTubeMusicUrl:
    """Tests for YouTube Music URL validation."""

    @pytest.mark.parametrize(
        "url",
        [
            # Playlist URLs
            "https://music.youtube.com/playlist?list=OLAK5uy_test123",
            "https://www.youtube.com/playlist?list=PLtest123",
            "https://m.youtube.com/playlist?list=PLtest123",
            "https://music.youtube.com/browse/MPREb_test123",
            # Single track URLs
            "https://music.youtube.com/watch?v=Vgpv5PtWsn4",
            "https://www.youtube.com/watch?v=GkTWxDB21cA",
            "https://youtube.com/watch?v=GkTWxDB21cA",
            "https://m.youtube.com/watch?v=GkTWxDB21cA",
            # URLs with extra params
            "https://music.youtube.com/watch?v=abc123&si=xyz789",
            "https://music.youtube.com/watch?v=abc123&list=PLtest123",
            # youtu.be short URLs
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?si=abc",
            # Path-based URLs (shorts, live, embed)
            "https://youtube.com/shorts/dQw4w9WgXcQ",
            "https://m.youtube.com/shorts/dQw4w9WgXcQ",
            "https://youtube.com/live/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube-nocookie.com/embed/dQw4w9WgXcQ",
        ],
        ids=[
            "music_youtube_playlist",
            "youtube_playlist",
            "mobile_youtube_playlist",
            "music_youtube_browse",
            "music_youtube_watch",
            "youtube_watch",
            "youtube_watch_no_www",
            "mobile_youtube_watch",
            "watch_extra_params",
            "watch_with_list",
            "youtu_be_short",
            "youtu_be_with_si",
            "youtube_shorts",
            "mobile_youtube_shorts",
            "youtube_live",
            "youtube_embed",
            "youtube_nocookie_embed",
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
