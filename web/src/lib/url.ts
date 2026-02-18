// Must match backend validation in packages/api/src/yubal_api/schemas/jobs.py
// and core validation in packages/yubal/src/yubal/utils/url.py
export const YOUTUBE_URL_PATTERN =
  /^https?:\/\/(music\.youtube\.com\/(playlist\?list=|browse\/|watch\?v=)|(?:www\.|m\.)?youtube\.com\/(playlist\?list=|watch\?v=|shorts\/|live\/|embed\/|e\/|v\/|vi\/)|youtu\.be\/|(?:www\.)?youtube-nocookie\.com\/embed\/)[\w-]+/;

export function isValidUrl(url: string): boolean {
  return YOUTUBE_URL_PATTERN.test(url);
}
