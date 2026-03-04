export function rawHtml(html: string): Element {
  return new DOMParser().parseFromString(html.trim(), "text/html").body
    .firstElementChild!;
}
