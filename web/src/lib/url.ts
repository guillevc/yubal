// Must match backend validation in packages/api/src/yubal_api/schemas/jobs.py
export const YOUTUBE_MUSIC_URL_PATTERN =
  /^https?:\/\/(music\.youtube\.com\/(playlist\?list=|browse\/|watch\?v=)|(?:www\.)?youtube\.com\/(playlist\?list=|watch\?v=))[\w-]+/;

export function isValidUrl(url: string): boolean {
  return YOUTUBE_MUSIC_URL_PATTERN.test(url);
}
