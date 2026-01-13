"""Tests for factory functions and public API."""

from ytmeta import (
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
        import ytmeta

        # Factory function
        assert hasattr(ytmeta, "create_extractor")

        # Client
        assert hasattr(ytmeta, "YTMusicClient")
        assert hasattr(ytmeta, "YTMusicProtocol")

        # Services
        assert hasattr(ytmeta, "MetadataExtractorService")

        # Models
        assert hasattr(ytmeta, "TrackMetadata")
        assert hasattr(ytmeta, "VideoType")

        # Config
        assert hasattr(ytmeta, "APIConfig")

        # Exceptions
        assert hasattr(ytmeta, "YTMetaError")
        assert hasattr(ytmeta, "PlaylistParseError")
        assert hasattr(ytmeta, "PlaylistNotFoundError")
        assert hasattr(ytmeta, "APIError")

    def test_version_available(self) -> None:
        """Version should be available."""
        import ytmeta

        assert hasattr(ytmeta, "__version__")
        assert ytmeta.__version__ == "0.1.0"
