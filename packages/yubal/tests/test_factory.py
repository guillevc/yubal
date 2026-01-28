"""Tests for factory functions and public API."""

from yubal import (
    APIConfig,
    MetadataExtractorService,
    create_extractor,
)


class TestCreateExtractor:
    """Tests for create_extractor factory function."""

    def test_creates_extractor_with_defaults(self) -> None:
        """Should create extractor with default config."""
        extractor = create_extractor()

        assert isinstance(extractor, MetadataExtractorService)

    def test_creates_extractor_with_custom_config(self) -> None:
        """Should create extractor with custom config."""
        config = APIConfig(search_limit=5, ignore_spelling=False)
        extractor = create_extractor(config)

        assert isinstance(extractor, MetadataExtractorService)


class TestPublicAPI:
    """Tests for public API exports."""

    def test_all_expected_exports_available(self) -> None:
        """All documented exports should be available."""
        import yubal

        # Factory functions
        assert hasattr(yubal, "create_extractor")
        assert hasattr(yubal, "create_downloader")
        assert hasattr(yubal, "create_playlist_downloader")

        # Services (only high-level)
        assert hasattr(yubal, "MetadataExtractorService")
        assert hasattr(yubal, "PlaylistDownloadService")

        # Models
        assert hasattr(yubal, "TrackMetadata")
        assert hasattr(yubal, "VideoType")
        assert hasattr(yubal, "ContentKind")
        assert hasattr(yubal, "ExtractProgress")
        assert hasattr(yubal, "DownloadProgress")
        assert hasattr(yubal, "DownloadResult")
        assert hasattr(yubal, "DownloadStatus")

        # Config
        assert hasattr(yubal, "APIConfig")
        assert hasattr(yubal, "AudioCodec")
        assert hasattr(yubal, "DownloadConfig")
        assert hasattr(yubal, "PlaylistDownloadConfig")

        # Exceptions
        assert hasattr(yubal, "YTMetaError")
        assert hasattr(yubal, "PlaylistParseError")
        assert hasattr(yubal, "PlaylistNotFoundError")
        assert hasattr(yubal, "APIError")

    def test_internal_not_exported(self) -> None:
        """Internal implementation details should not be exported."""
        import yubal

        # Client is internal (use factory functions instead)
        assert not hasattr(yubal, "YTMusicClient")
        assert not hasattr(yubal, "YTMusicProtocol")

        # Internal services (use PlaylistDownloadService instead)
        assert not hasattr(yubal, "DownloadService")
        assert not hasattr(yubal, "PlaylistArtifactsService")

        # Downloader backend is internal
        assert not hasattr(yubal, "YTDLPDownloader")
        assert not hasattr(yubal, "DownloaderProtocol")
        assert not hasattr(yubal, "tag_track")
