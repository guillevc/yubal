"""Tests for lyrics fetchers and composite service."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ytmusicapi.exceptions import YTMusicServerError
from ytmusicapi.models.lyrics import LyricLine
from yubal.services.lyrics import (
    LrclibFetcher,
    LyricsQuery,
    LyricsService,
    YouTubeMusicLyricsFetcher,
    _format_lrc_timestamp,
    _payload_to_lrc,
    _timed_lyrics_to_lrc,
)


class TestFormatLrcTimestamp:
    @pytest.mark.parametrize(
        ("ms", "expected"),
        [
            (0, "[00:00.00]"),
            (9200, "[00:09.20]"),
            (10630, "[00:10.63]"),
            (60001, "[01:00.00]"),
            (123450, "[02:03.45]"),
            (3_600_000, "[60:00.00]"),
            (-100, "[00:00.00]"),
        ],
    )
    def test_format(self, ms: int, expected: str) -> None:
        assert _format_lrc_timestamp(ms) == expected


class TestTimedLyricsToLrc:
    def test_joins_lines(self) -> None:
        lines = [
            LyricLine(text="I was a liar", start_time=9200, end_time=10630, id=1),
            LyricLine(
                text="I gave in to the fire", start_time=10680, end_time=12540, id=2
            ),
        ]
        result = _timed_lyrics_to_lrc(lines)
        assert result == "[00:09.20]I was a liar\n[00:10.68]I gave in to the fire"


class TestPayloadToLrc:
    def test_timed_payload(self) -> None:
        payload = {
            "lyrics": [
                LyricLine(text="hello", start_time=1000, end_time=2000, id=1),
            ],
            "hasTimestamps": True,
            "source": "Source: LyricFind",
        }
        assert _payload_to_lrc(payload) == "[00:01.00]hello"

    def test_plain_payload(self) -> None:
        payload = {
            "lyrics": "just plain text",
            "hasTimestamps": False,
            "source": "Source: LyricFind",
        }
        assert _payload_to_lrc(payload) == "just plain text"

    def test_empty_payload(self) -> None:
        assert _payload_to_lrc({"lyrics": "", "hasTimestamps": False}) is None
        assert _payload_to_lrc({"lyrics": [], "hasTimestamps": True}) is None
        assert _payload_to_lrc({}) is None


class TestYouTubeMusicLyricsFetcher:
    def test_returns_lrc_for_timed_lyrics(self) -> None:
        client = MagicMock()
        client.get_lyrics_browse_id.return_value = "MPLYt_abc"
        client.get_lyrics.return_value = {
            "lyrics": [
                LyricLine(text="hello world", start_time=9200, end_time=10000, id=1),
            ],
            "hasTimestamps": True,
            "source": "Source: LyricFind",
        }
        fetcher = YouTubeMusicLyricsFetcher(client)
        query = LyricsQuery(title="t", artist="a", duration_seconds=200, video_id="vid")
        assert fetcher.fetch(query) == "[00:09.20]hello world"
        client.get_lyrics_browse_id.assert_called_once_with("vid")
        client.get_lyrics.assert_called_once_with("MPLYt_abc")

    def test_returns_plain_text_for_untimed(self) -> None:
        client = MagicMock()
        client.get_lyrics_browse_id.return_value = "MPLYt_abc"
        client.get_lyrics.return_value = {
            "lyrics": "verse one\nverse two",
            "hasTimestamps": False,
            "source": "Source: LyricFind",
        }
        fetcher = YouTubeMusicLyricsFetcher(client)
        query = LyricsQuery(title="t", artist="a", duration_seconds=200, video_id="vid")
        assert fetcher.fetch(query) == "verse one\nverse two"

    def test_returns_none_when_no_video_id(self) -> None:
        client = MagicMock()
        fetcher = YouTubeMusicLyricsFetcher(client)
        query = LyricsQuery(title="t", artist="a", duration_seconds=200)
        assert fetcher.fetch(query) is None
        client.get_lyrics_browse_id.assert_not_called()

    def test_returns_none_when_no_browse_id(self) -> None:
        client = MagicMock()
        client.get_lyrics_browse_id.return_value = None
        fetcher = YouTubeMusicLyricsFetcher(client)
        query = LyricsQuery(title="t", artist="a", duration_seconds=200, video_id="vid")
        assert fetcher.fetch(query) is None
        client.get_lyrics.assert_not_called()

    def test_swallows_api_error(self) -> None:
        client = MagicMock()
        client.get_lyrics_browse_id.side_effect = YTMusicServerError("boom")
        fetcher = YouTubeMusicLyricsFetcher(client)
        query = LyricsQuery(title="t", artist="a", duration_seconds=200, video_id="vid")
        assert fetcher.fetch(query) is None


def _fake_fetcher(name: str, returns: str | None) -> MagicMock:
    mock = MagicMock()
    mock.name = name
    mock.fetch.return_value = returns
    return mock


class TestLyricsServiceComposite:
    def test_first_success_short_circuits(self) -> None:
        first = _fake_fetcher("first", "[00:00.00]hi")
        second = _fake_fetcher("second", None)
        service = LyricsService(fetchers=[first, second])
        assert service.fetch_lyrics("t", "a", 200) == "[00:00.00]hi"
        first.fetch.assert_called_once()
        second.fetch.assert_not_called()

    def test_falls_through_on_none(self) -> None:
        first = _fake_fetcher("first", None)
        second = _fake_fetcher("second", "fallback lyrics")
        service = LyricsService(fetchers=[first, second])
        assert service.fetch_lyrics("t", "a", 200, video_id="vid") == "fallback lyrics"
        first.fetch.assert_called_once()
        second.fetch.assert_called_once()
        # Both fetchers should receive the same query payload.
        passed = second.fetch.call_args.args[0]
        assert passed.video_id == "vid"
        assert passed.title == "t"

    def test_all_none_returns_none(self) -> None:
        first = _fake_fetcher("first", None)
        service = LyricsService(fetchers=[first])
        assert service.fetch_lyrics("t", "a", 200) is None

    def test_logs_source_on_hit(self, caplog: pytest.LogCaptureFixture) -> None:
        service = LyricsService(fetchers=[_fake_fetcher("lrclib", "lyrics body")])
        with caplog.at_level("INFO", logger="yubal.services.lyrics"):
            service.fetch_lyrics("Song", "Artist", 200)
        assert "Found lyrics from lrclib for 'Song' by Artist" in caplog.text

    def test_logs_fallback_chain_on_first_miss(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        first = _fake_fetcher("lrclib", None)
        second = _fake_fetcher("YouTube Music", "lyrics body")
        service = LyricsService(fetchers=[first, second])
        with caplog.at_level("INFO", logger="yubal.services.lyrics"):
            service.fetch_lyrics("Song", "Artist", 200)
        assert "No lyrics from lrclib" in caplog.text
        assert "falling back to YouTube Music" in caplog.text
        assert "Found lyrics from YouTube Music" in caplog.text

    def test_logs_all_sources_when_all_miss(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        first = _fake_fetcher("lrclib", None)
        second = _fake_fetcher("YouTube Music", None)
        service = LyricsService(fetchers=[first, second])
        with caplog.at_level("INFO", logger="yubal.services.lyrics"):
            service.fetch_lyrics("Song", "Artist", 200)
        assert (
            "No lyrics found for 'Song' by Artist (tried: lrclib, YouTube Music)"
            in caplog.text
        )

    def test_default_uses_lrclib_fetcher(self) -> None:
        service = LyricsService()
        assert len(service._fetchers) == 1
        assert isinstance(service._fetchers[0], LrclibFetcher)

    def test_save_lyrics_writes_lrc(self, tmp_path: Path) -> None:
        service = LyricsService(fetchers=[])
        audio = tmp_path / "track.opus"
        audio.touch()
        out = service.save_lyrics("[00:00.00]hi", audio)
        assert out == tmp_path / "track.lrc"
        assert out.read_text() == "[00:00.00]hi"


class TestLrclibFetcher:
    def test_returns_synced_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        response = MagicMock(
            status_code=200,
            json=lambda: {
                "syncedLyrics": "[00:00.00]line",
                "plainLyrics": "line",
            },
        )
        response.raise_for_status = MagicMock()
        monkeypatch.setattr(
            "yubal.services.lyrics.httpx.get", lambda *a, **kw: response
        )
        fetcher = LrclibFetcher()
        result = fetcher.fetch(LyricsQuery("t", "a", 200))
        assert result == "[00:00.00]line"

    def test_returns_plain_when_no_synced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        response = MagicMock(
            status_code=200,
            json=lambda: {"syncedLyrics": None, "plainLyrics": "verse"},
        )
        response.raise_for_status = MagicMock()
        monkeypatch.setattr(
            "yubal.services.lyrics.httpx.get", lambda *a, **kw: response
        )
        assert LrclibFetcher().fetch(LyricsQuery("t", "a", 200)) == "verse"

    def test_returns_none_on_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = MagicMock(status_code=404)
        monkeypatch.setattr(
            "yubal.services.lyrics.httpx.get", lambda *a, **kw: response
        )
        assert LrclibFetcher().fetch(LyricsQuery("t", "a", 200)) is None
