"""Tests for MetadataExtractorService."""

import logging

import pytest
from conftest import MockYTMusicClient
from pydantic import ValidationError
from yubal.exceptions import CancellationError
from yubal.models.cancel import CancelToken
from yubal.models.enums import MatchResult, SkipReason, VideoType
from yubal.models.track import TrackMetadata
from yubal.models.ytmusic import Album, Artist, Playlist, SearchResult, Thumbnail
from yubal.services import MetadataExtractorService
from yubal.services.extractor import (
    _format_artists,
    _get_square_thumbnail,
    _upscale_thumbnail_url,
)


def extract_all(
    service: MetadataExtractorService,
    url: str,
    max_items: int | None = None,
) -> list[TrackMetadata]:
    """Collect all extracted tracks into a list (test convenience helper)."""
    return [p.track for p in service.extract(url, max_items=max_items) if p.track]


class TestMetadataExtractorService:
    """Tests for MetadataExtractorService."""

    def test_extract_basic(
        self,
        mock_client: MockYTMusicClient,
    ) -> None:
        """Should extract metadata from a playlist."""
        service = MetadataExtractorService(mock_client)
        progress_list = list(
            service.extract("https://music.youtube.com/playlist?list=PLtest123")
        )

        assert len(progress_list) == 1
        assert progress_list[0].track is not None
        assert progress_list[0].track.title == "Test Song"
        assert mock_client.get_playlist_calls == ["PLtest123"]

    def test_extract_all_convenience_method(
        self,
        mock_client: MockYTMusicClient,
    ) -> None:
        """Should extract all tracks using convenience method."""
        service = MetadataExtractorService(mock_client)
        tracks = extract_all(
            service, "https://music.youtube.com/playlist?list=PLtest123"
        )

        assert len(tracks) == 1
        assert tracks[0].title == "Test Song"
        assert mock_client.get_playlist_calls == ["PLtest123"]

    def test_extract_with_album_lookup(
        self,
        mock_client: MockYTMusicClient,
        sample_playlist: Playlist,
    ) -> None:
        """Should look up album details."""
        service = MetadataExtractorService(mock_client)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have called get_album for the track's album
        assert len(mock_client.get_album_calls) == 1
        assert tracks[0].album == "Test Album"
        assert tracks[0].year == "2024"

    def test_extract_determines_video_type_atv(
        self,
        mock_client: MockYTMusicClient,
    ) -> None:
        """Should detect ATV video type."""
        service = MetadataExtractorService(mock_client)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Sample playlist track has MUSIC_VIDEO_TYPE_ATV
        assert tracks[0].video_type == VideoType.ATV

    def test_extract_yields_progress(
        self,
        mock_client: MockYTMusicClient,
    ) -> None:
        """Should yield progress updates."""
        service = MetadataExtractorService(mock_client)
        progress_list = list(
            service.extract("https://music.youtube.com/playlist?list=PLtest")
        )

        assert len(progress_list) == 1
        assert progress_list[0].current == 1
        assert progress_list[0].total == 1
        assert progress_list[0].track is not None

    def test_extract_progress_model_is_frozen(
        self,
        mock_client: MockYTMusicClient,
    ) -> None:
        """ExtractProgress should be immutable."""
        service = MetadataExtractorService(mock_client)
        progress_list = list(
            service.extract("https://music.youtube.com/playlist?list=PLtest")
        )

        with pytest.raises(ValidationError):
            progress_list[0].current = 999

    def test_extract_handles_missing_album(
        self,
        sample_playlist: Playlist,
        sample_search_result: SearchResult,
        sample_album: Album,
    ) -> None:
        """Should search for album when not in playlist track."""
        # Create a playlist track without album
        playlist_no_album = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist", "id": "a1"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                        # No album field
                    }
                ]
            }
        )

        mock = MockYTMusicClient(
            playlist=playlist_no_album,
            album=sample_album,
            search_results=[sample_search_result],
        )

        service = MetadataExtractorService(mock)
        extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have searched for the song
        assert len(mock.search_songs_calls) == 1
        assert "Artist" in mock.search_songs_calls[0]
        assert "Test Song" in mock.search_songs_calls[0]

    def test_extract_searches_album_when_album_id_is_null(
        self,
        sample_album: Album,
        sample_search_result: SearchResult,
    ) -> None:
        """Should search for album when album ref has null id."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist", "id": "a1"}],
                        "album": {"name": "Some Album", "id": None},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = MockYTMusicClient(
            playlist=playlist,
            album=sample_album,
            search_results=[sample_search_result],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have searched for the song since album_id is None
        assert len(mock.search_songs_calls) == 1
        assert len(tracks) == 1

    def test_extract_fallback_when_no_album_found(
        self,
    ) -> None:
        """Should create fallback metadata when album can't be found."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Unknown Song",
                        "artists": [{"name": "Unknown Artist"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        # No album in search results
        mock = MockYTMusicClient(
            playlist=playlist,
            album=None,
            search_results=[],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        assert len(tracks) == 1
        assert tracks[0].title == "Unknown Song"
        assert tracks[0].album == "Unknown Album"  # Fallback when no album found
        assert tracks[0].track_number is None

    def test_extract_continues_on_track_error(
        self,
    ) -> None:
        """Should continue processing when one track fails."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Good Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    },
                    {
                        "videoId": "v2",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Another Song",
                        "artists": [{"name": "Artist"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 200,
                    },
                ]
            }
        )

        # Album lookup will fail
        mock = MockYTMusicClient(
            playlist=playlist,
            album=None,
            search_results=[],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Both tracks should be returned (with fallback for the one without album)
        assert len(tracks) == 2

    def test_extract_matches_track_in_album_by_title(
        self,
        sample_playlist: Playlist,
        sample_album: Album,
    ) -> None:
        """Should match playlist track to album track by title."""
        mock = MockYTMusicClient(
            playlist=sample_playlist,
            album=sample_album,
            search_results=[],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have gotten track number from album track
        assert tracks[0].track_number == 5

    def test_extract_atv_id_from_search(
        self,
    ) -> None:
        """Should capture ATV video ID from search results."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "omv123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        search_result = SearchResult.model_validate(
            {
                "videoId": "atv456",
                "videoType": "MUSIC_VIDEO_TYPE_ATV",
                "title": "Test Song",
                "artists": [{"name": "Artist"}],
                "album": {"id": "alb1", "name": "Album"},
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "albumtrack1",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(
            playlist=playlist,
            album=album,
            search_results=[search_result],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have captured the ATV ID from search
        assert tracks[0].atv_video_id == "atv456"
        assert tracks[0].video_type == VideoType.OMV

    def test_extract_album_playlist_atv_no_duplicate_ids(
        self,
    ) -> None:
        """Should not duplicate ATV ID as OMV ID for album playlists.

        Album playlists contain ATV tracks where the playlist track video_id
        and album track video_id are the same. In this case, omv_video_id
        should be None since there's no separate OMV.
        """
        # Album playlist track (ATV) with same video_id as album track
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "atv123",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        # Album track has the same video_id (as is typical for album playlists)
        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "atv123",  # Same as playlist track
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(
            playlist=playlist,
            album=album,
            search_results=[],
        )

        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # ATV ID should be set
        assert tracks[0].atv_video_id == "atv123"
        # OMV ID should be None (not the same as ATV)
        assert tracks[0].omv_video_id is None
        assert tracks[0].video_type == VideoType.ATV

    def test_extract_determines_video_type_omv(
        self,
    ) -> None:
        """Should detect OMV video type when not ATV."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "omv123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "omv123",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        assert tracks[0].video_type == VideoType.OMV
        assert tracks[0].omv_video_id == "omv123"
        assert tracks[0].atv_video_id is None

    def test_extract_matches_track_by_duration_when_title_differs(
        self,
    ) -> None:
        """Should match track by duration when title doesn't match."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Different Title",  # Title doesn't match
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 237,  # Unique duration
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Original Title",  # Different title
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 3,
                        "duration_seconds": 237,  # Matching duration
                    },
                    {
                        "videoId": "album_v2",
                        "title": "Another Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 4,
                        "duration_seconds": 300,  # Different duration
                    },
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have matched by duration and gotten track number
        assert tracks[0].track_number == 3
        assert tracks[0].omv_video_id == "album_v1"

    def test_extract_no_duration_match_when_multiple_tracks_same_duration(
        self,
    ) -> None:
        """Should not match by duration when multiple tracks have same duration."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Unknown Title",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Song One",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,  # Same duration
                    },
                    {
                        "videoId": "album_v2",
                        "title": "Song Two",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 2,
                        "duration_seconds": 180,  # Same duration - ambiguous!
                    },
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should NOT have matched - track_number should be None
        assert tracks[0].track_number is None
        # Falls back to track.video_id since no album_track matched
        assert tracks[0].omv_video_id == "v1"

    def test_extract_title_matching_case_insensitive(
        self,
    ) -> None:
        """Should match titles case-insensitively."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "TEST SONG",  # Uppercase
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "test song",  # Lowercase
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 7,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have matched despite case difference
        assert tracks[0].track_number == 7
        assert tracks[0].omv_video_id == "album_v1"

    def test_extract_title_matching_strips_whitespace(
        self,
    ) -> None:
        """Should match titles after stripping whitespace."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "  Test Song  ",  # Extra whitespace
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Test Song",  # No extra whitespace
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 2,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have matched after stripping whitespace
        assert tracks[0].track_number == 2

    def test_extract_search_returns_omv_result(
        self,
    ) -> None:
        """Should not capture ATV ID when search returns OMV."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "omv123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        # No album - triggers search
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        # Search returns OMV, not ATV
        search_result = SearchResult.model_validate(
            {
                "videoId": "search_omv",
                "videoType": "MUSIC_VIDEO_TYPE_OMV",  # OMV result
                "title": "Test Song",
                "artists": [{"name": "Artist"}],
                "album": {"id": "alb1", "name": "Album"},
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(
            playlist=playlist, album=album, search_results=[search_result]
        )
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # ATV should be None since search returned OMV
        assert tracks[0].atv_video_id is None
        assert tracks[0].omv_video_id == "album_v1"

    def test_extract_fallback_for_atv_track(
        self,
    ) -> None:
        """Fallback metadata for ATV track should set atv_video_id."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "atv123",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        # No album
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        # No album found anywhere
        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should use fallback with ATV ID set correctly
        assert tracks[0].atv_video_id == "atv123"
        assert tracks[0].omv_video_id is None
        assert tracks[0].video_type == VideoType.ATV

    def test_extract_atv_track_with_different_omv_in_album(
        self,
    ) -> None:
        """ATV track should get separate OMV ID from album when different."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "atv123",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        # Album track has a DIFFERENT video ID (the OMV)
        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "omv456",  # Different from playlist track!
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Both IDs should be set and different
        assert tracks[0].atv_video_id == "atv123"
        assert tracks[0].omv_video_id == "omv456"
        assert tracks[0].video_type == VideoType.ATV

    def test_extract_video_type_none_skips_track(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should skip track when video_type is missing."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v123",
                        # No videoType field
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)

        with caplog.at_level(logging.DEBUG):
            tracks = extract_all(
                service, "https://music.youtube.com/playlist?list=PLtest"
            )

        # Track should be skipped due to missing video type
        assert len(tracks) == 0
        assert "Missing video type" in caplog.text

    def test_extract_fuzzy_match_high_confidence(
        self,
    ) -> None:
        """Should match track by fuzzy title with high confidence (>80%)."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Song Title (Remaster)",  # Similar but not exact
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 999,  # Different duration
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Song Title (Remastered)",  # Very similar
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 3,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have matched via fuzzy matching
        assert tracks[0].track_number == 3
        assert tracks[0].omv_video_id == "album_v1"

    def test_extract_fuzzy_match_medium_confidence_with_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should match with warning for medium confidence (50-80%)."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "My Song - Radio Edit",  # Moderately similar
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 999,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "My Song (Extended Mix)",  # Different version
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 5,
                        "duration_seconds": 300,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        with caplog.at_level(logging.WARNING):
            tracks = extract_all(
                service, "https://music.youtube.com/playlist?list=PLtest"
            )

        # Should match but with warning
        assert tracks[0].track_number == 5
        assert "Low confidence track match" in caplog.text

    def test_extract_fuzzy_match_low_confidence_rejected(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should reject fuzzy match with low confidence (<50%)."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Completely Different Title",  # Very different
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 999,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Another Song Entirely",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        with caplog.at_level(logging.WARNING):
            tracks = extract_all(
                service, "https://music.youtube.com/playlist?list=PLtest"
            )

        # Should NOT have matched - track_number should be None
        assert tracks[0].track_number is None
        assert "No confident match" in caplog.text

    def test_extract_fuzzy_match_selects_best_match(
        self,
    ) -> None:
        """Should select the track with highest similarity score."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Love Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 999,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "album_v1",
                        "title": "Hate Song",  # Less similar
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    },
                    {
                        "videoId": "album_v2",
                        "title": "Love Song (Live)",  # More similar
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 2,
                        "duration_seconds": 200,
                    },
                    {
                        "videoId": "album_v3",
                        "title": "Other Track",  # Not similar
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 3,
                        "duration_seconds": 220,
                    },
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have selected "Love Song (Live)" as best match
        assert tracks[0].track_number == 2
        assert tracks[0].omv_video_id == "album_v2"

    def test_extract_fuzzy_match_empty_album_tracks(
        self,
    ) -> None:
        """Should handle empty album tracks list gracefully."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [],  # Empty tracks list
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should fall back to original track info
        assert tracks[0].track_number is None
        assert tracks[0].omv_video_id == "v1"

    def test_extract_album_fetch_failure_uses_fallback(
        self,
    ) -> None:
        """Should use fallback when album fetch fails."""

        class FailingAlbumClient(MockYTMusicClient):
            def get_album(self, album_id: str) -> Album:
                raise Exception("Album fetch failed")

        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "My Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = FailingAlbumClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have used fallback (album name from track, not full album)
        assert tracks[0].album == "My Album"
        assert tracks[0].track_number is None  # No album lookup

    def test_extract_search_failure_continues(
        self,
    ) -> None:
        """Should continue when search fails."""

        class FailingSearchClient(MockYTMusicClient):
            def search_songs(self, query: str) -> list[SearchResult]:
                raise Exception("Search failed")

        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Test Song",
                        "artists": [{"name": "Artist"}],
                        # No album - triggers search
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = FailingSearchClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have returned fallback metadata
        assert len(tracks) == 1
        assert tracks[0].title == "Test Song"
        assert tracks[0].album == "Unknown Album"  # Fallback when no album found

    def test_extract_low_artist_match_marks_unmatched(
        self,
    ) -> None:
        """Should mark track as unmatched when artist match is low."""

        class MismatchedArtistClient(MockYTMusicClient):
            def search_songs(self, query: str) -> list[SearchResult]:
                return [
                    SearchResult.model_validate(
                        {
                            "videoId": "atv123",
                            "videoType": "MUSIC_VIDEO_TYPE_ATV",
                            "title": "Mercury Retrograde",
                            "artists": [{"name": "Ghostemane"}],
                            "album": {
                                "id": "MPREb_wrong",
                                "name": "Mercury Retrograde",
                            },
                        }
                    )
                ]

        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "omv123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Mercury Retrograde",
                        "artists": [{"name": "Wiz Khalifa"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 200,
                    }
                ]
            }
        )

        mock = MismatchedArtistClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        assert len(tracks) == 1
        assert tracks[0].match_result == MatchResult.UNMATCHED
        assert tracks[0].title == "Mercury Retrograde"
        assert tracks[0].year is None
        assert tracks[0].track_number is None

    def test_extract_matches_track_by_video_id(
        self,
    ) -> None:
        """Should match track by video_id even when title differs."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "omv123",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Different Playlist Title",  # Different from album
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 999,  # Different duration too
                    }
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "omv123",  # Same video_id as playlist track
                        "title": "Original Album Title",  # Different title
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 5,
                        "duration_seconds": 180,  # Different duration
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)
        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have matched by video_id and gotten track number
        assert tracks[0].track_number == 5
        assert tracks[0].total_tracks == 1
        assert tracks[0].omv_video_id == "omv123"

    def test_extract_skips_ugc_video_type(
        self,
    ) -> None:
        """Should skip UGC video types with SkipReason.UGC."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "ugc123",
                        "videoType": "MUSIC_VIDEO_TYPE_UGC",
                        "title": "User Upload",
                        "artists": [{"name": "Some User"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)

        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # UGC track should be skipped
        assert len(tracks) == 0

        # Verify skip reason is UGC (not UNSUPPORTED_VIDEO_TYPE)
        metadata, skip_reason = service._extract_single_track(playlist.tracks[0])
        assert metadata is None
        assert skip_reason is SkipReason.UGC

    def test_extract_skips_official_source_music_video_type(
        self,
    ) -> None:
        """Should skip OFFICIAL_SOURCE_MUSIC video types with UNSUPPORTED_VIDEO_TYPE."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "osm123",
                        "videoType": "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC",
                        "title": "Official Source Track",
                        "artists": [{"name": "Label"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)

        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # OFFICIAL_SOURCE_MUSIC track should be skipped
        assert len(tracks) == 0

        # Truly unsupported types use UNSUPPORTED_VIDEO_TYPE (not UGC)
        metadata, skip_reason = service._extract_single_track(playlist.tracks[0])
        assert metadata is None
        assert skip_reason is SkipReason.UNSUPPORTED_VIDEO_TYPE

    def test_extract_skips_unknown_video_type(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should skip unknown video types."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "unk123",
                        "videoType": "MUSIC_VIDEO_TYPE_UNKNOWN_FUTURE",
                        "title": "Unknown Type Track",
                        "artists": [{"name": "Artist"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock)

        with caplog.at_level(logging.DEBUG):
            tracks = extract_all(
                service, "https://music.youtube.com/playlist?list=PLtest"
            )

        # Unknown type track should be skipped
        assert len(tracks) == 0
        assert "Unknown video type" in caplog.text

    def test_extract_mixed_video_types_skips_unsupported(
        self,
    ) -> None:
        """Should process supported types and skip unsupported in mixed playlists."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "atv1",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Good ATV Track",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    },
                    {
                        "videoId": "ugc1",
                        "videoType": "MUSIC_VIDEO_TYPE_UGC",
                        "title": "Bad UGC Track",
                        "artists": [{"name": "User"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 200,
                    },
                    {
                        "videoId": "omv1",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "title": "Good OMV Track",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb2", "name": "Album 2"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 220,
                    },
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "atv1",
                        "title": "Good ATV Track",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        # Should have 2 tracks (ATV and OMV), UGC skipped
        assert len(tracks) == 2
        assert tracks[0].video_type == VideoType.ATV
        assert tracks[1].video_type == VideoType.OMV


class TestExtractorCancellation:
    """Tests for cancellation during metadata extraction."""

    def _make_multi_track_playlist(self, count: int = 5) -> Playlist:
        """Create a playlist with multiple tracks."""
        tracks = []
        for i in range(count):
            tracks.append(
                {
                    "videoId": f"v{i}",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": f"Song {i}",
                    "artists": [{"name": "Artist"}],
                    "album": {"id": "alb1", "name": "Album"},
                    "thumbnails": [
                        {"url": "https://t.jpg", "width": 120, "height": 90}
                    ],
                    "duration_seconds": 180,
                }
            )
        return Playlist.model_validate({"tracks": tracks})

    def test_pre_cancelled_token_raises_immediately(self) -> None:
        """Should raise CancellationError immediately with a pre-cancelled token."""
        playlist = self._make_multi_track_playlist(5)
        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "v0",
                        "title": "Song 0",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )
        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        token = CancelToken()
        token.cancel()

        with pytest.raises(CancellationError):
            list(
                service.extract(
                    "https://music.youtube.com/playlist?list=PLtest",
                    cancel_token=token,
                )
            )

    def test_cancel_mid_extraction_stops_generator(self) -> None:
        """Should stop yielding tracks when cancelled mid-extraction."""
        playlist = self._make_multi_track_playlist(10)
        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": f"v{i}",
                        "title": f"Song {i}",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": i + 1,
                        "duration_seconds": 180,
                    }
                    for i in range(10)
                ],
            }
        )
        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        token = CancelToken()
        extracted = []

        with pytest.raises(CancellationError):
            for progress in service.extract(
                "https://music.youtube.com/playlist?list=PLtest",
                cancel_token=token,
            ):
                extracted.append(progress.track)
                if len(extracted) == 3:
                    token.cancel()

        # Should have extracted some tracks but not all 10
        assert 0 < len(extracted) < 10

    def test_no_cancel_token_extracts_normally(self) -> None:
        """Should work normally when cancel_token is None."""
        playlist = self._make_multi_track_playlist(3)
        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": f"v{i}",
                        "title": f"Song {i}",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": i + 1,
                        "duration_seconds": 180,
                    }
                    for i in range(3)
                ],
            }
        )
        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock)

        tracks = [
            p.track
            for p in service.extract(
                "https://music.youtube.com/playlist?list=PLtest",
                cancel_token=None,
            )
            if p.track
        ]
        assert len(tracks) == 3


class TestFormatArtists:
    """Tests for _format_artists function."""

    def test_single_artist(self) -> None:
        """Should format a single artist correctly."""
        artists = [Artist(name="Taylor Swift", id="123")]
        assert _format_artists(artists) == "Taylor Swift"

    def test_multiple_artists(self) -> None:
        """Should join multiple artists with semicolons."""
        artists = [
            Artist(name="John Lennon", id="1"),
            Artist(name="Paul McCartney", id="2"),
        ]
        assert _format_artists(artists) == "John Lennon; Paul McCartney"

    def test_empty_list(self) -> None:
        """Should return empty string for empty list."""
        assert _format_artists([]) == ""

    def test_artist_without_id(self) -> None:
        """Should handle artists without ID."""
        artists = [Artist(name="Unknown Artist", id=None)]
        assert _format_artists(artists) == "Unknown Artist"

    def test_filters_empty_names(self) -> None:
        """Should skip artists with empty names."""
        artists = [
            Artist(name="Valid Artist", id="1"),
            Artist(name="", id="2"),
        ]
        assert _format_artists(artists) == "Valid Artist"


class TestUpscaleThumbnailUrl:
    """Tests for _upscale_thumbnail_url function."""

    def test_replaces_size_parameters(self) -> None:
        """Should replace w/h parameters in Google thumbnail URLs."""
        url = "https://lh3.googleusercontent.com/abc123=w120-h120-l90-rj"
        result = _upscale_thumbnail_url(url)
        assert result == "https://lh3.googleusercontent.com/abc123=w544-h544-l90-rj"

    def test_custom_size(self) -> None:
        """Should use specified size."""
        url = "https://lh3.googleusercontent.com/abc123=w120-h120-l90-rj"
        result = _upscale_thumbnail_url(url, size=1200)
        assert result == "https://lh3.googleusercontent.com/abc123=w1200-h1200-l90-rj"

    def test_preserves_url_without_size_params(self) -> None:
        """Should return URL unchanged if no size parameters found."""
        url = "https://example.com/image.jpg"
        assert _upscale_thumbnail_url(url) == url

    def test_handles_various_sizes(self) -> None:
        """Should replace any numeric size values."""
        url = "https://lh3.googleusercontent.com/abc=w226-h226-l90-rj"
        result = _upscale_thumbnail_url(url)
        assert result == "https://lh3.googleusercontent.com/abc=w544-h544-l90-rj"


class TestGetSquareThumbnail:
    """Tests for _get_square_thumbnail function."""

    def test_returns_largest_square_upscaled(self) -> None:
        """Should return the largest square thumbnail, upscaled."""
        thumbnails = [
            Thumbnail(
                url="https://lh3.googleusercontent.com/a=w120-h120-l90-rj",
                width=120,
                height=120,
            ),
            Thumbnail(
                url="https://lh3.googleusercontent.com/b=w544-h544-l90-rj",
                width=544,
                height=544,
            ),
            Thumbnail(
                url="https://lh3.googleusercontent.com/c=w320-h320-l90-rj",
                width=320,
                height=320,
            ),
        ]
        assert (
            _get_square_thumbnail(thumbnails)
            == "https://lh3.googleusercontent.com/b=w544-h544-l90-rj"
        )

    def test_prefers_square_over_rectangular(self) -> None:
        """Should prefer square thumbnails over larger rectangular ones."""
        thumbnails = [
            Thumbnail(url="https://rect.jpg", width=1280, height=720),
            Thumbnail(
                url="https://lh3.googleusercontent.com/a=w544-h544-l90-rj",
                width=544,
                height=544,
            ),
        ]
        assert (
            _get_square_thumbnail(thumbnails)
            == "https://lh3.googleusercontent.com/a=w544-h544-l90-rj"
        )

    def test_falls_back_to_last_thumbnail(self) -> None:
        """Should return last thumbnail if no square ones exist."""
        thumbnails = [
            Thumbnail(url="https://small.jpg", width=120, height=90),
            Thumbnail(url="https://large.jpg", width=1280, height=720),
        ]
        assert _get_square_thumbnail(thumbnails) == "https://large.jpg"

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None for empty list."""
        assert _get_square_thumbnail([]) is None

    def test_single_square_thumbnail(self) -> None:
        """Should work with a single square thumbnail."""
        thumbnails = [Thumbnail(url="https://only.jpg", width=544, height=544)]
        assert _get_square_thumbnail(thumbnails) == "https://only.jpg"

    def test_upscales_small_thumbnail(self) -> None:
        """Should upscale a small thumbnail URL to 544px."""
        thumbnails = [
            Thumbnail(
                url="https://lh3.googleusercontent.com/a=w120-h120-l90-rj",
                width=120,
                height=120,
            ),
        ]
        assert (
            _get_square_thumbnail(thumbnails)
            == "https://lh3.googleusercontent.com/a=w544-h544-l90-rj"
        )


class TestUGCDownload:
    """Tests for UGC (User Generated Content) track handling."""

    def _make_ugc_playlist(self) -> Playlist:
        """Create a playlist containing a UGC track."""
        return Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "ugc123",
                        "videoType": "MUSIC_VIDEO_TYPE_UGC",
                        "title": "User Upload",
                        "artists": [{"name": "Some User"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )

    def test_ugc_skipped_when_download_ugc_disabled(self) -> None:
        """Should skip UGC tracks with SkipReason.UGC when download_ugc is False."""
        playlist = self._make_ugc_playlist()
        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock, download_ugc=False)

        # Verify _extract_single_track returns UGC skip reason
        track = playlist.tracks[0]
        metadata, skip_reason = service._extract_single_track(track)
        assert metadata is None
        assert skip_reason is SkipReason.UGC

    def test_ugc_extracted_when_download_ugc_enabled(self) -> None:
        """Should extract UGC tracks as unofficial when download_ugc is True."""
        playlist = self._make_ugc_playlist()
        mock = MockYTMusicClient(playlist=playlist, album=None, search_results=[])
        service = MetadataExtractorService(mock, download_ugc=True)

        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        assert len(tracks) == 1
        assert tracks[0].match_result == MatchResult.UNOFFICIAL
        assert tracks[0].title == "User Upload"
        assert tracks[0].source_video_id == "ugc123"
        assert tracks[0].video_type == VideoType.UGC
        # UGC tracks have no official OMV/ATV
        assert tracks[0].omv_video_id is None
        assert tracks[0].atv_video_id is None
        # video_id property falls back to source_video_id
        assert tracks[0].video_id == "ugc123"

    def test_ugc_mixed_with_supported_types(self) -> None:
        """Should extract both supported and UGC tracks when enabled."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "atv1",
                        "videoType": "MUSIC_VIDEO_TYPE_ATV",
                        "title": "Good ATV Track",
                        "artists": [{"name": "Artist"}],
                        "album": {"id": "alb1", "name": "Album"},
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    },
                    {
                        "videoId": "ugc1",
                        "videoType": "MUSIC_VIDEO_TYPE_UGC",
                        "title": "UGC Track",
                        "artists": [{"name": "User"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 200,
                    },
                ]
            }
        )

        album = Album.model_validate(
            {
                "title": "Album",
                "artists": [{"name": "Artist"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "atv1",
                        "title": "Good ATV Track",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 180,
                    }
                ],
            }
        )

        mock = MockYTMusicClient(playlist=playlist, album=album, search_results=[])
        service = MetadataExtractorService(mock, download_ugc=True)

        tracks = extract_all(service, "https://music.youtube.com/playlist?list=PLtest")

        assert len(tracks) == 2
        assert tracks[0].match_result == MatchResult.MATCHED
        assert tracks[0].video_type == VideoType.ATV
        assert tracks[1].match_result == MatchResult.UNOFFICIAL
        assert tracks[1].video_type == VideoType.UGC
