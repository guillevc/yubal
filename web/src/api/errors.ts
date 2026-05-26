// Extract the human-readable message from an API error body. The API returns
// either an ErrorResponse ({error, message}) for application errors or an
// HTTPValidationError ({detail: [{msg}]}) for request-shape errors. Falls
// back to the provided default when neither shape matches.
export function errorMessage(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null) {
    const e = error as { message?: unknown; detail?: unknown };
    if (typeof e.message === "string" && e.message.trim()) {
      return e.message;
    }
    if (Array.isArray(e.detail)) {
      const first = e.detail[0] as { msg?: unknown } | undefined;
      if (first && typeof first.msg === "string" && first.msg.trim()) {
        return first.msg;
      }
    }
  }
  return fallback;
}
