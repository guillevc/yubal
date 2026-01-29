export interface SearchArtist {
  name: string;
  id?: string;
}

export interface SearchResult {
  resultType?: string;
  category?: string;
  title?: string;
  name?: string;
  artist?: string;
  artists?: SearchArtist[];
  album?: { name: string; id?: string };
  author?: string;
  playlistId?: string;
  browseId?: string;
  videoId?: string;
  duration?: string;
  year?: string;
  itemCount?: string;
  thumbnails?: Array<{ url: string; width?: number; height?: number }>;
  [key: string]: unknown;
}

export interface SearchResponse {
  results: SearchResult[];
}

export interface SearchSuggestionsResponse {
  suggestions: Array<
    | string
    | {
        text: string;
        runs?: Array<{ text: string; bold?: boolean }>;
      }
  >;
}

export interface SearchOptions {
  filter?: string;
  scope?: string;
  limit?: number;
  ignoreSpelling?: boolean;
}

export async function searchYtMusic(
  query: string,
  options: SearchOptions = {},
): Promise<SearchResponse> {
  const params = new URLSearchParams({ query });

  if (options.filter) params.set("filter", options.filter);
  if (options.scope) params.set("scope", options.scope);
  if (options.limit) params.set("limit", String(options.limit));
  if (options.ignoreSpelling !== undefined) {
    params.set("ignore_spelling", String(options.ignoreSpelling));
  }

  const response = await fetch(`/api/search?${params.toString()}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Search failed");
  }

  return response.json() as Promise<SearchResponse>;
}

export async function searchSuggestions(
  query: string,
): Promise<SearchSuggestionsResponse> {
  const params = new URLSearchParams({ query, detailed_runs: "true" });
  const response = await fetch(`/api/search/suggestions?${params.toString()}`);

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Suggestions failed");
  }

  return response.json() as Promise<SearchSuggestionsResponse>;
}
