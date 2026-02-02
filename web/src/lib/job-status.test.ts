import { describe, expect, test } from "bun:test";
import type { JobStatus } from "@/api/jobs";
import { isActive, isFinished, isRunning } from "./job-status";

const ALL_STATUSES: JobStatus[] = [
  "pending",
  "fetching_info",
  "downloading",
  "importing",
  "completed",
  "failed",
  "cancelled",
];

const FINISHED_STATUSES: JobStatus[] = ["completed", "failed", "cancelled"];
const ACTIVE_STATUSES: JobStatus[] = [
  "pending",
  "fetching_info",
  "downloading",
  "importing",
];
const RUNNING_STATUSES: JobStatus[] = [
  "fetching_info",
  "downloading",
  "importing",
];

describe("isFinished", () => {
  test.each(FINISHED_STATUSES)("returns true for %s", (status) => {
    expect(isFinished(status)).toBe(true);
  });

  test.each(ACTIVE_STATUSES)("returns false for %s", (status) => {
    expect(isFinished(status)).toBe(false);
  });
});

describe("isActive", () => {
  test.each(ACTIVE_STATUSES)("returns true for %s", (status) => {
    expect(isActive(status)).toBe(true);
  });

  test.each(FINISHED_STATUSES)("returns false for %s", (status) => {
    expect(isActive(status)).toBe(false);
  });

  test("isActive and isFinished are mutually exclusive", () => {
    for (const status of ALL_STATUSES) {
      expect(isActive(status)).toBe(!isFinished(status));
    }
  });
});

describe("isRunning", () => {
  test.each(RUNNING_STATUSES)("returns true for %s", (status) => {
    expect(isRunning(status)).toBe(true);
  });

  test("returns false for pending", () => {
    expect(isRunning("pending")).toBe(false);
  });

  test.each(FINISHED_STATUSES)("returns false for %s", (status) => {
    expect(isRunning(status)).toBe(false);
  });

  test("isRunning is a subset of isActive", () => {
    for (const status of ALL_STATUSES) {
      if (isRunning(status)) {
        expect(isActive(status)).toBe(true);
      }
    }
  });
});
