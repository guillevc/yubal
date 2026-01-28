import { describe, expect, test } from "bun:test";
import type { JobStatus } from "@/api/jobs";
import { isActive, isFinished } from "./job-status";

const ALL_STATUSES: JobStatus[] = [
  "pending",
  "fetching_info",
  "downloading",
  "importing",
  "completed",
  "failed",
  "cancelled",
];

describe("isFinished", () => {
  test("returns true for completed status", () => {
    expect(isFinished("completed")).toBe(true);
  });

  test("returns true for failed status", () => {
    expect(isFinished("failed")).toBe(true);
  });

  test("returns true for cancelled status", () => {
    expect(isFinished("cancelled")).toBe(true);
  });

  test("returns false for pending status", () => {
    expect(isFinished("pending")).toBe(false);
  });

  test("returns false for fetching_info status", () => {
    expect(isFinished("fetching_info")).toBe(false);
  });

  test("returns false for downloading status", () => {
    expect(isFinished("downloading")).toBe(false);
  });

  test("returns false for importing status", () => {
    expect(isFinished("importing")).toBe(false);
  });
});

describe("isActive", () => {
  test("returns true for active statuses", () => {
    expect(isActive("pending")).toBe(true);
    expect(isActive("fetching_info")).toBe(true);
    expect(isActive("downloading")).toBe(true);
    expect(isActive("importing")).toBe(true);
  });

  test("returns false for finished statuses", () => {
    expect(isActive("completed")).toBe(false);
    expect(isActive("failed")).toBe(false);
    expect(isActive("cancelled")).toBe(false);
  });

  test("isActive and isFinished are mutually exclusive", () => {
    for (const status of ALL_STATUSES) {
      expect(isActive(status)).toBe(!isFinished(status));
    }
  });
});
