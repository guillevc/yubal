export const YOUTUBE_MUSIC_URL_PATTERN =
  /^https?:\/\/(music\.)?youtube\.com\/(playlist\?list=|watch\?v=|browse\/VL)/;

export function isValidUrl(url: string): boolean {
  return YOUTUBE_MUSIC_URL_PATTERN.test(url);
}
