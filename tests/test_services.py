"""Tests for services."""

import logging

import pytest
from pydantic import ValidationError

from tests.conftest import MockYTMusicClient
from ytmeta.models.domain import VideoType
from ytmeta.models.ytmusic import Album, Playlist, SearchResult
from ytmeta.services import MetadataExtractorService


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
        tracks = service.extract_all(
            "https://music.youtube.com/playlist?list=PLtest123"
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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
            progress_list[0].current = 999  # type: ignore

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
        service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Should have searched for the song
        assert len(mock.search_songs_calls) == 1
        assert "Artist" in mock.search_songs_calls[0]
        assert "Test Song" in mock.search_songs_calls[0]

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        assert len(tracks) == 1
        assert tracks[0].title == "Unknown Song"
        assert tracks[0].album == ""  # No album found
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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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

        with caplog.at_level(logging.WARNING):
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Should match but with warning
        assert tracks[0].track_number == 5
        assert "Fuzzy match" in caplog.text

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
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Should have returned fallback metadata
        assert len(tracks) == 1
        assert tracks[0].title == "Test Song"
        assert tracks[0].album == ""  # No album found

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
        tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Should have matched by video_id and gotten track number
        assert tracks[0].track_number == 5
        assert tracks[0].total_tracks == 1
        assert tracks[0].omv_video_id == "omv123"

    def test_extract_skips_ugc_video_type(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should skip UGC (User Generated Content) video types with warning."""
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

        with caplog.at_level(logging.WARNING):
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # UGC track should be skipped
        assert len(tracks) == 0
        assert "Unsupported video type 'UGC'" in caplog.text

    def test_extract_skips_official_source_music_video_type(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should skip OFFICIAL_SOURCE_MUSIC video types with warning."""
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

        with caplog.at_level(logging.WARNING):
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # OFFICIAL_SOURCE_MUSIC track should be skipped
        assert len(tracks) == 0
        assert "Unsupported video type 'OFFICIAL_SOURCE_MUSIC'" in caplog.text

    def test_extract_skips_unknown_video_type(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should skip unknown video types with warning."""
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

        with caplog.at_level(logging.WARNING):
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Unknown type track should be skipped
        assert len(tracks) == 0
        assert "Unknown video type" in caplog.text

    def test_extract_mixed_video_types_skips_unsupported(
        self,
        caplog: pytest.LogCaptureFixture,
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

        with caplog.at_level(logging.WARNING):
            tracks = service.extract_all("https://music.youtube.com/playlist?list=PLtest")

        # Should have 2 tracks (ATV and OMV), UGC skipped
        assert len(tracks) == 2
        assert tracks[0].video_type == VideoType.ATV
        assert tracks[1].video_type == VideoType.OMV
        assert "Unsupported video type 'UGC'" in caplog.text
