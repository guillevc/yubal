"""Tests for exceptions."""

from ytmeta.exceptions import (
    APIError,
    PlaylistNotFoundError,
    PlaylistParseError,
    YTMetaError,
)


class TestExceptionStatusCodes:
    """Tests for HTTP status codes on exceptions."""

    def test_base_error_status_code(self) -> None:
        """YTMetaError should have 500 status code."""
        error = YTMetaError("test")
        assert error.status_code == 500

    def test_playlist_parse_error_status_code(self) -> None:
        """PlaylistParseError should have 400 status code."""
        error = PlaylistParseError("invalid url")
        assert error.status_code == 400

    def test_playlist_not_found_error_status_code(self) -> None:
        """PlaylistNotFoundError should have 404 status code."""
        error = PlaylistNotFoundError("not found")
        assert error.status_code == 404

    def test_api_error_status_code(self) -> None:
        """APIError should have 502 status code."""
        error = APIError("upstream failure")
        assert error.status_code == 502


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """All custom exceptions should inherit from YTMetaError."""
        assert issubclass(PlaylistParseError, YTMetaError)
        assert issubclass(PlaylistNotFoundError, YTMetaError)
        assert issubclass(APIError, YTMetaError)

    def test_catch_all_with_base_class(self) -> None:
        """Should be able to catch all errors with YTMetaError."""
        errors = [
            PlaylistParseError("test"),
            PlaylistNotFoundError("test"),
            APIError("test"),
        ]

        for error in errors:
            try:
                raise error
            except YTMetaError as e:
                assert e.message == "test"

    def test_exception_message_attribute(self) -> None:
        """Exceptions should have message attribute."""
        error = YTMetaError("test message")
        assert error.message == "test message"
        assert str(error) == "test message"
