"""Tests for exceptions."""

import pytest
from yubal.exceptions import (
    APIError,
    PlaylistNotFoundError,
    PlaylistParseError,
    YTMetaError,
)


class TestExceptionStatusCodes:
    """Tests for HTTP status codes on exceptions."""

    @pytest.mark.parametrize(
        ("exception_class", "expected_status"),
        [
            (YTMetaError, 500),
            (PlaylistParseError, 400),
            (PlaylistNotFoundError, 404),
            (APIError, 502),
        ],
        ids=["base_error", "parse_error", "not_found", "api_error"],
    )
    def test_exception_status_codes(
        self, exception_class: type[YTMetaError], expected_status: int
    ) -> None:
        """Each exception type should have the correct HTTP status code."""
        error = exception_class("test message")
        assert error.status_code == expected_status


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    @pytest.mark.parametrize(
        "exception_class",
        [PlaylistParseError, PlaylistNotFoundError, APIError],
    )
    def test_all_exceptions_inherit_from_base(
        self, exception_class: type[YTMetaError]
    ) -> None:
        """All custom exceptions should inherit from YTMetaError."""
        assert issubclass(exception_class, YTMetaError)

    @pytest.mark.parametrize(
        "exception_class",
        [PlaylistParseError, PlaylistNotFoundError, APIError],
    )
    def test_catch_all_with_base_class(
        self, exception_class: type[YTMetaError]
    ) -> None:
        """Should be able to catch all errors with YTMetaError."""
        with pytest.raises(YTMetaError) as exc_info:
            raise exception_class("test message")
        assert exc_info.value.message == "test message"

    def test_exception_message_attribute(self) -> None:
        """Exceptions should have message attribute and string representation."""
        error = YTMetaError("test message")
        assert error.message == "test message"
        assert str(error) == "test message"
