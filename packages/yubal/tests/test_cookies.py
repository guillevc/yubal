"""Tests for cookie conversion utilities."""

from pathlib import Path

from yubal.utils.cookies import (
    build_cookie_header,
    cookies_to_ytmusic_auth,
    generate_sapisidhash,
    get_sapisid,
    is_authenticated_cookies,
    parse_netscape_cookies,
)


class TestParseNetscapeCookies:
    """Tests for parse_netscape_cookies."""

    def test_parses_valid_cookies(self, tmp_path: Path) -> None:
        """Should parse valid Netscape format cookies."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\tvalue1\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\tHSID\tvalue2\n"
        )

        result = parse_netscape_cookies(cookies_file)

        assert result == {"SID": "value1", "HSID": "value2"}

    def test_skips_comments(self, tmp_path: Path) -> None:
        """Should skip comment lines."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            "# This is a comment\n"
            "# Another comment\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\tvalue1\n"
        )

        result = parse_netscape_cookies(cookies_file)

        assert result == {"SID": "value1"}

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        """Should skip empty lines."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            "\n.youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\tvalue1\n\n"
        )

        result = parse_netscape_cookies(cookies_file)

        assert result == {"SID": "value1"}

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty dict for missing file."""
        cookies_file = tmp_path / "nonexistent.txt"

        result = parse_netscape_cookies(cookies_file)

        assert result == {}

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        """Should skip lines with insufficient fields."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            "malformed line\n.youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\tvalue1\n"
        )

        result = parse_netscape_cookies(cookies_file)

        assert result == {"SID": "value1"}


class TestBuildCookieHeader:
    """Tests for build_cookie_header."""

    def test_builds_header_from_cookies(self) -> None:
        """Should build cookie header string."""
        cookies = {"SID": "value1", "HSID": "value2"}

        result = build_cookie_header(cookies)

        assert "SID=value1" in result
        assert "HSID=value2" in result
        assert "; " in result

    def test_handles_empty_cookies(self) -> None:
        """Should return empty string for empty cookies."""
        result = build_cookie_header({})
        assert result == ""


class TestGetSapisid:
    """Tests for get_sapisid."""

    def test_returns_secure_3papisid(self) -> None:
        """Should prefer __Secure-3PAPISID."""
        cookies = {
            "__Secure-3PAPISID": "secure_value",
            "SAPISID": "old_value",
        }

        result = get_sapisid(cookies)

        assert result == "secure_value"

    def test_falls_back_to_sapisid(self) -> None:
        """Should fall back to SAPISID if __Secure-3PAPISID missing."""
        cookies = {"SAPISID": "old_value"}

        result = get_sapisid(cookies)

        assert result == "old_value"

    def test_returns_none_if_missing(self) -> None:
        """Should return None if no SAPISID cookie."""
        cookies = {"SID": "value"}

        result = get_sapisid(cookies)

        assert result is None


class TestGenerateSapisidhash:
    """Tests for generate_sapisidhash."""

    def test_generates_valid_format(self) -> None:
        """Should generate SAPISIDHASH in correct format."""
        result = generate_sapisidhash("test_sapisid")

        assert result.startswith("SAPISIDHASH ")
        parts = result.split(" ")[1].split("_")
        assert len(parts) == 2
        # Timestamp should be numeric
        assert parts[0].isdigit()
        # Hash should be hex
        assert all(c in "0123456789abcdef" for c in parts[1])


class TestCookiesToYtmusicAuth:
    """Tests for cookies_to_ytmusic_auth."""

    def test_returns_auth_dict_with_valid_cookies(self, tmp_path: Path) -> None:
        """Should return auth dict when cookies are valid."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\t__Secure-3PAPISID\ttest_sapisid\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\ttest_sid\n"
        )

        result = cookies_to_ytmusic_auth(cookies_file)

        assert result is not None
        assert "Authorization" in result
        assert result["Authorization"].startswith("SAPISIDHASH ")
        assert "Cookie" in result
        assert "__Secure-3PAPISID=test_sapisid" in result["Cookie"]
        assert result["x-origin"] == "https://music.youtube.com"

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Should return None for missing cookies file."""
        cookies_file = tmp_path / "nonexistent.txt"

        result = cookies_to_ytmusic_auth(cookies_file)

        assert result is None

    def test_returns_none_without_sapisid(self, tmp_path: Path) -> None:
        """Should return None if no SAPISID cookie."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\ttest_sid\n"
        )

        result = cookies_to_ytmusic_auth(cookies_file)

        assert result is None


class TestIsAuthenticatedCookies:
    """Tests for is_authenticated_cookies."""

    def test_returns_true_with_sapisid(self, tmp_path: Path) -> None:
        """Should return True when SAPISID present."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(
            ".youtube.com\tTRUE\t/\tTRUE\t1735689600\t__Secure-3PAPISID\tvalue\n"
        )

        result = is_authenticated_cookies(cookies_file)

        assert result is True

    def test_returns_false_without_sapisid(self, tmp_path: Path) -> None:
        """Should return False when SAPISID missing."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text(".youtube.com\tTRUE\t/\tTRUE\t1735689600\tSID\tvalue\n")

        result = is_authenticated_cookies(cookies_file)

        assert result is False

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        """Should return False for missing file."""
        cookies_file = tmp_path / "nonexistent.txt"

        result = is_authenticated_cookies(cookies_file)

        assert result is False
