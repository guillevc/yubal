import { describe, expect, test } from "bun:test";
import { isValidUrl, YOUTUBE_MUSIC_URL_PATTERN } from "./url";

describe("isValidUrl", () => {
  describe("valid YouTube Music URLs", () => {
    test("accepts playlist URLs", () => {
      expect(
        isValidUrl("https://music.youtube.com/playlist?list=OLAK5uy_abc123"),
      ).toBe(true);
      expect(isValidUrl("http://music.youtube.com/playlist?list=PLxyz")).toBe(
        true,
      );
    });

    test("accepts watch URLs", () => {
      expect(isValidUrl("https://music.youtube.com/watch?v=dQw4w9WgXcQ")).toBe(
        true,
      );
      expect(isValidUrl("http://music.youtube.com/watch?v=abc123")).toBe(true);
    });

    test("accepts browse/VL URLs (album URLs)", () => {
      expect(isValidUrl("https://music.youtube.com/browse/VLPLxyz123")).toBe(
        true,
      );
    });
  });

  describe("valid regular YouTube URLs", () => {
    test("accepts playlist URLs", () => {
      expect(isValidUrl("https://youtube.com/playlist?list=PLxyz123")).toBe(
        true,
      );
      expect(isValidUrl("http://youtube.com/playlist?list=abc")).toBe(true);
    });

    test("accepts watch URLs", () => {
      expect(isValidUrl("https://youtube.com/watch?v=dQw4w9WgXcQ")).toBe(true);
    });

    test("accepts browse/VL URLs", () => {
      expect(isValidUrl("https://youtube.com/browse/VLPLxyz")).toBe(true);
    });
  });

  describe("invalid URLs", () => {
    test("rejects empty string", () => {
      expect(isValidUrl("")).toBe(false);
    });

    test("rejects non-YouTube URLs", () => {
      expect(isValidUrl("https://spotify.com/playlist/abc")).toBe(false);
      expect(isValidUrl("https://soundcloud.com/track/xyz")).toBe(false);
    });

    test("rejects YouTube URLs without valid path", () => {
      expect(isValidUrl("https://youtube.com/")).toBe(false);
      expect(isValidUrl("https://youtube.com/channel/abc")).toBe(false);
      expect(isValidUrl("https://youtube.com/shorts/abc")).toBe(false);
    });

    test("rejects youtu.be short URLs", () => {
      expect(isValidUrl("https://youtu.be/dQw4w9WgXcQ")).toBe(false);
    });

    test("rejects malformed URLs", () => {
      expect(isValidUrl("not a url")).toBe(false);
      expect(isValidUrl("youtube.com/watch?v=abc")).toBe(false); // missing protocol
    });
  });
});

describe("YOUTUBE_MUSIC_URL_PATTERN", () => {
  test("is a valid RegExp", () => {
    expect(YOUTUBE_MUSIC_URL_PATTERN).toBeInstanceOf(RegExp);
  });
});
