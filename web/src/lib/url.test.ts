import { describe, expect, test } from "bun:test";
import { isValidUrl, YOUTUBE_URL_PATTERN } from "./url";

const VALID_YOUTUBE_MUSIC_URLS = [
  "https://music.youtube.com/playlist?list=OLAK5uy_abc123",
  "http://music.youtube.com/playlist?list=PLxyz",
  "https://music.youtube.com/browse/VLPLxyz123",
  "https://music.youtube.com/browse/MPREb_abc123",
  "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
];

const VALID_YOUTUBE_URLS = [
  "https://youtube.com/playlist?list=PLxyz123",
  "http://youtube.com/playlist?list=abc",
  "https://www.youtube.com/playlist?list=PLxyz",
  "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
];

const VALID_MOBILE_URLS = [
  "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
  "https://m.youtube.com/playlist?list=PLxyz123",
  "https://m.youtube.com/shorts/dQw4w9WgXcQ",
];

const VALID_SHORT_URLS = [
  "https://youtu.be/dQw4w9WgXcQ",
  "http://youtu.be/abc123",
];

const VALID_PATH_BASED_URLS = [
  "https://youtube.com/shorts/dQw4w9WgXcQ",
  "https://www.youtube.com/shorts/dQw4w9WgXcQ",
  "https://youtube.com/live/dQw4w9WgXcQ",
  "https://www.youtube.com/live/dQw4w9WgXcQ",
  "https://youtube.com/embed/dQw4w9WgXcQ",
  "https://www.youtube.com/embed/dQw4w9WgXcQ",
  "https://youtube-nocookie.com/embed/dQw4w9WgXcQ",
  "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
  "https://youtube.com/e/dQw4w9WgXcQ",
  "https://youtube.com/v/dQw4w9WgXcQ",
  "https://youtube.com/vi/dQw4w9WgXcQ",
];

const INVALID_URLS = [
  ["empty string", ""],
  ["Spotify URL", "https://spotify.com/playlist/abc"],
  ["SoundCloud URL", "https://soundcloud.com/track/xyz"],
  ["YouTube homepage", "https://youtube.com/"],
  ["YouTube channel", "https://youtube.com/channel/abc"],
  ["plain text", "not a url"],
  ["missing protocol", "youtube.com/watch?v=abc"],
  ["YouTube browse (not music)", "https://youtube.com/browse/VLPLxyz"],
] as const;

describe("isValidUrl", () => {
  describe("valid YouTube Music URLs", () => {
    test.each(VALID_YOUTUBE_MUSIC_URLS)("accepts %s", (url) => {
      expect(isValidUrl(url)).toBe(true);
    });
  });

  describe("valid YouTube URLs", () => {
    test.each(VALID_YOUTUBE_URLS)("accepts %s", (url) => {
      expect(isValidUrl(url)).toBe(true);
    });
  });

  describe("valid mobile URLs", () => {
    test.each(VALID_MOBILE_URLS)("accepts %s", (url) => {
      expect(isValidUrl(url)).toBe(true);
    });
  });

  describe("valid youtu.be short URLs", () => {
    test.each(VALID_SHORT_URLS)("accepts %s", (url) => {
      expect(isValidUrl(url)).toBe(true);
    });
  });

  describe("valid path-based URLs (shorts, live, embed)", () => {
    test.each(VALID_PATH_BASED_URLS)("accepts %s", (url) => {
      expect(isValidUrl(url)).toBe(true);
    });
  });

  describe("invalid URLs", () => {
    test.each(INVALID_URLS)("rejects %s", (_description, url) => {
      expect(isValidUrl(url)).toBe(false);
    });
  });
});

describe("YOUTUBE_URL_PATTERN", () => {
  test("is a valid RegExp", () => {
    expect(YOUTUBE_URL_PATTERN).toBeInstanceOf(RegExp);
  });
});
