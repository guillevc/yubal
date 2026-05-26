import { describe, expect, test } from "bun:test";
import { errorMessage } from "./errors";

describe("errorMessage", () => {
  test("returns ErrorResponse.message when present", () => {
    const body = {
      error: "authentication_required",
      message: "Authentication failed. Please re-upload your cookies.",
    };
    expect(errorMessage(body, "fallback")).toBe(
      "Authentication failed. Please re-upload your cookies.",
    );
  });

  test("returns HTTPValidationError detail[0].msg when present", () => {
    const body = { detail: [{ msg: "URL is not a supported YouTube URL" }] };
    expect(errorMessage(body, "fallback")).toBe(
      "URL is not a supported YouTube URL",
    );
  });

  test("falls back when message is empty/whitespace", () => {
    expect(errorMessage({ message: "   " }, "fallback")).toBe("fallback");
  });

  test("falls back on unknown shape", () => {
    expect(errorMessage({ unexpected: true }, "fallback")).toBe("fallback");
    expect(errorMessage(null, "fallback")).toBe("fallback");
    expect(errorMessage(undefined, "fallback")).toBe("fallback");
    expect(errorMessage("not an object", "fallback")).toBe("fallback");
  });
});
