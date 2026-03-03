export type ApiResponse<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: string; message: string };

async function request<T>(
  url: string,
  init?: RequestInit,
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(url, init);
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    let error = "unknown_error";
    let message = res.statusText;
    try {
      const body = await res.json();
      error = body.error ?? error;
      message = body.message ?? body.detail ?? message;
    } catch {
      // response wasn't JSON
    }
    return { ok: false, status: res.status, error, message };
  } catch {
    return {
      ok: false,
      status: 0,
      error: "network_error",
      message: "Could not connect to server",
    };
  }
}

export function createJob(baseUrl: string, tabUrl: string) {
  return request(`${baseUrl}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: tabUrl }),
  });
}

export function createSubscription(baseUrl: string, tabUrl: string) {
  return request(`${baseUrl}/api/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: tabUrl }),
  });
}

export function healthCheck(baseUrl: string) {
  return request(`${baseUrl}/api/health`);
}

export type ContentInfo = {
  title: string;
  artist: string;
  kind: "album" | "playlist" | "track";
  year: number | null;
  track_count: number | null;
  thumbnail_url: string | null;
};

export function getContentInfo(baseUrl: string, url: string) {
  return request<ContentInfo>(
    `${baseUrl}/api/info?url=${encodeURIComponent(url)}`,
  );
}
