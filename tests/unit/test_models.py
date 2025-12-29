"""Tests for yubal.core.models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from yubal.core.enums import JobStatus
from yubal.core.models import (
    AlbumInfo,
    DownloadResult,
    Job,
    LogEntry,
    SyncResult,
    TagResult,
)


class TestAlbumInfo:
    """Tests for AlbumInfo model."""

    def test_minimal_valid_creation(self):
        """AlbumInfo can be created with only required fields."""
        album = AlbumInfo(title="Test Album", artist="Test Artist", track_count=10)

        assert album.title == "Test Album"
        assert album.artist == "Test Artist"
        assert album.track_count == 10
        # Defaults
        assert album.year is None
        assert album.playlist_id == ""
        assert album.url == ""
        assert album.thumbnail_url is None
        assert album.audio_codec is None
        assert album.audio_bitrate is None

    def test_full_creation(self):
        """AlbumInfo can be created with all fields."""
        album = AlbumInfo(
            title="Abbey Road",
            artist="The Beatles",
            year=1969,
            track_count=17,
            playlist_id="PLxxxxx",
            url="https://music.youtube.com/playlist?list=PLxxxxx",
            thumbnail_url="https://example.com/cover.jpg",
            audio_codec="opus",
            audio_bitrate=128,
        )

        assert album.title == "Abbey Road"
        assert album.artist == "The Beatles"
        assert album.year == 1969
        assert album.track_count == 17
        assert album.audio_codec == "opus"
        assert album.audio_bitrate == 128

    def test_missing_required_field_raises_error(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumInfo(title="Test")  # type: ignore[call-arg]  # intentionally missing

        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "artist" in field_names
        assert "track_count" in field_names

    def test_json_serialization(self):
        """AlbumInfo can be serialized to JSON and back."""
        album = AlbumInfo(
            title="Test Album",
            artist="Test Artist",
            track_count=10,
            year=2024,
        )

        json_str = album.model_dump_json()
        restored = AlbumInfo.model_validate_json(json_str)

        assert restored == album


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_successful_download(self):
        """DownloadResult for a successful download."""
        result = DownloadResult(
            success=True,
            output_dir="/tmp/download",
            downloaded_files=["/tmp/download/01.opus", "/tmp/download/02.opus"],
        )

        assert result.success is True
        assert result.output_dir == "/tmp/download"
        assert len(result.downloaded_files) == 2
        assert result.error is None
        assert result.cancelled is False

    def test_failed_download(self):
        """DownloadResult for a failed download."""
        result = DownloadResult(
            success=False,
            output_dir="/tmp/download",
            error="Network timeout",
        )

        assert result.success is False
        assert result.error == "Network timeout"

    def test_cancelled_download(self):
        """DownloadResult for a cancelled download."""
        result = DownloadResult(
            success=False,
            output_dir="/tmp/download",
            cancelled=True,
            error="Download cancelled",
        )

        assert result.success is False
        assert result.cancelled is True

    def test_with_album_info(self):
        """DownloadResult can include album info."""
        album = AlbumInfo(title="Test", artist="Artist", track_count=5)
        result = DownloadResult(
            success=True,
            output_dir="/tmp/download",
            album_info=album,
        )

        assert result.album_info is not None
        assert result.album_info.title == "Test"


class TestTagResult:
    """Tests for TagResult model."""

    def test_successful_tag(self):
        """TagResult for a successful tagging operation."""
        result = TagResult(
            success=True,
            source_dir="/tmp/download",
            dest_dir="/music/Artist/Album",
            album_name="Album",
            artist_name="Artist",
            track_count=10,
        )

        assert result.success is True
        assert result.dest_dir == "/music/Artist/Album"
        assert result.track_count == 10

    def test_failed_tag(self):
        """TagResult for a failed tagging operation."""
        result = TagResult(
            success=False,
            source_dir="/tmp/download",
            error="Beets import failed",
        )

        assert result.success is False
        assert result.error == "Beets import failed"
        assert result.dest_dir is None


class TestSyncResult:
    """Tests for SyncResult model."""

    def test_successful_sync(self):
        """SyncResult for a complete successful sync."""
        album_info = AlbumInfo(title="Album", artist="Artist", track_count=10)
        download_result = DownloadResult(
            success=True,
            output_dir="/tmp/download",
            album_info=album_info,
        )
        tag_result = TagResult(
            success=True,
            source_dir="/tmp/download",
            dest_dir="/music/Artist/Album",
        )

        sync = SyncResult(
            success=True,
            download_result=download_result,
            tag_result=tag_result,
            album_info=album_info,
            destination="/music/Artist/Album",
        )

        assert sync.success is True
        assert sync.destination == "/music/Artist/Album"
        assert sync.download_result is not None
        assert sync.tag_result is not None

    def test_failed_sync(self):
        """SyncResult for a failed sync."""
        sync = SyncResult(
            success=False,
            error="Download failed: Network error",
        )

        assert sync.success is False
        assert sync.error == "Download failed: Network error"


class TestLogEntry:
    """Tests for LogEntry model."""

    def test_creation(self):
        """LogEntry can be created with all fields."""
        now = datetime.now(UTC)
        entry = LogEntry(
            timestamp=now,
            status="downloading",
            message="Track 1: 50% at 1.2MB/s",
        )

        assert entry.timestamp == now
        assert entry.status == "downloading"
        assert entry.message == "Track 1: 50% at 1.2MB/s"

    def test_json_serialization_preserves_timezone(self):
        """LogEntry timestamp should preserve UTC timezone."""
        now = datetime.now(UTC)
        entry = LogEntry(timestamp=now, status="test", message="test")

        json_str = entry.model_dump_json()
        restored = LogEntry.model_validate_json(json_str)

        # Timestamps should be equal (UTC preserved)
        assert restored.timestamp == now


class TestJob:
    """Tests for Job model."""

    def test_minimal_creation(self):
        """Job can be created with only required fields."""
        job = Job(id="job-123", url="https://music.youtube.com/playlist?list=PLxxx")

        assert job.id == "job-123"
        assert job.url == "https://music.youtube.com/playlist?list=PLxxx"
        # Defaults
        assert job.audio_format == "mp3"
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.album_info is None
        assert job.started_at is None
        assert job.completed_at is None
        # created_at should be auto-set
        assert job.created_at is not None

    def test_status_transition(self):
        """Job status can be updated (validate_assignment=True)."""
        job = Job(id="job-123", url="https://example.com")

        job.status = JobStatus.DOWNLOADING
        assert job.status == JobStatus.DOWNLOADING

        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED

    def test_progress_update(self):
        """Job progress can be updated."""
        job = Job(id="job-123", url="https://example.com")

        job.progress = 50.0
        assert job.progress == 50.0

        job.progress = 100.0
        assert job.progress == 100.0

    def test_with_album_info(self):
        """Job can have album_info attached."""
        album = AlbumInfo(title="Test Album", artist="Artist", track_count=5)
        job = Job(
            id="job-123",
            url="https://example.com",
            album_info=album,
        )

        assert job.album_info is not None
        assert job.album_info.title == "Test Album"

    def test_timestamps(self):
        """Job timestamps work correctly."""
        now = datetime.now(UTC)
        job = Job(
            id="job-123",
            url="https://example.com",
            created_at=now,
            started_at=now,
            completed_at=now,
        )

        assert job.created_at == now
        assert job.started_at == now
        assert job.completed_at == now

    def test_json_round_trip(self):
        """Job can be serialized and deserialized."""
        album = AlbumInfo(title="Test", artist="Artist", track_count=5)
        job = Job(
            id="job-123",
            url="https://example.com",
            status=JobStatus.COMPLETED,
            progress=100.0,
            album_info=album,
        )

        json_str = job.model_dump_json()
        restored = Job.model_validate_json(json_str)

        assert restored.id == job.id
        assert restored.status == job.status
        assert restored.progress == job.progress
        assert restored.album_info is not None
        assert restored.album_info.title == "Test"

    def test_is_finished_property_via_status(self):
        """Job status is_finished property works through Job."""
        job = Job(id="job-123", url="https://example.com")

        assert job.status.is_finished is False

        job.status = JobStatus.COMPLETED
        assert job.status.is_finished is True
