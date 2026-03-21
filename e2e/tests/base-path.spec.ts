import { test, expect } from "@playwright/test";

// Use "./" (relative) paths so Playwright resolves them against baseURL.
// With baseURL "http://host:port/yubal", "./" → "/yubal/", "./playlists" → "/yubal/playlists".
// With baseURL "http://host:port", "./" → "/", "./playlists" → "/playlists".

test("page loads at root with no errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  const failedAssets: string[] = [];
  page.on("response", (res) => {
    const url = new URL(res.url());
    if (res.status() >= 400 && /\.(js|css|svg)$/.test(url.pathname))
      failedAssets.push(`${res.status()} ${res.url()}`);
  });

  await page.goto("./");
  await expect(page.getByRole("navigation")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Downloads" })
  ).toBeVisible();
  expect(errors).toEqual([]);
  expect(failedAssets).toEqual([]);
});

test("deep link to /playlists loads correctly", async ({ page }) => {
  await page.goto("./playlists");
  await expect(page.getByRole("navigation")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "My playlists" })
  ).toBeVisible();
  expect(page.url()).toContain("/playlists");
});

test("client-side navigation does not stack paths", async ({
  page,
  baseURL,
}) => {
  await page.goto("./");
  await page.getByRole("link", { name: "My playlists" }).click();
  await expect(
    page.getByRole("heading", { name: "My playlists" })
  ).toBeVisible();
  expect(page.url()).toContain("/playlists");

  // Navigate back home
  await page.getByRole("link", { name: "yubal" }).click();
  await expect(
    page.getByRole("heading", { name: "Downloads" })
  ).toBeVisible();
  // URL should match the app root — no stacking like /yubal/yubal/
  const rootUrl = baseURL!.endsWith("/") ? baseURL! : baseURL + "/";
  expect(page.url()).toBe(rootUrl);
});

test("refresh on /playlists preserves page (SPA fallback)", async ({
  page,
}) => {
  await page.goto("./playlists");
  await expect(
    page.getByRole("heading", { name: "My playlists" })
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "My playlists" })
  ).toBeVisible();
  expect(page.url()).toContain("/playlists");
});

test("API health endpoint responds correctly", async ({ request, baseURL }) => {
  const base = baseURL!.replace(/\/$/, "");
  const res = await request.get(`${base}/api/health`);
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ status: "healthy" });
});

test("SSE connections use correct base path", async ({ page, baseURL }) => {
  const sseUrls: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/jobs/sse")) sseUrls.push(req.url());
  });

  await page.goto("./");
  await expect(page.getByRole("navigation")).toBeVisible();
  // Allow SSE to connect
  await page.waitForTimeout(1000);

  expect(sseUrls.length).toBeGreaterThan(0);
  expect(sseUrls[0]).toContain(baseURL!);
});
