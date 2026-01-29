export interface RelatedThumbnail {
  url: string;
  width?: number;
  height?: number;
}

export interface RelatedArtist {
  name: string;
  id?: string;
}

export interface RelatedItem {
  title?: string;
  name?: string;
  videoId?: string;
  browseId?: string;
  playlistId?: string;
  artists?: RelatedArtist[];
  thumbnails?: RelatedThumbnail[];
  year?: string;
  description?: string;
  subscribers?: string;
  duration?: string;
  itemCount?: string;
  [key: string]: unknown;
}

export interface RelatedSection {
  title?: string;
  contents?: RelatedItem[] | string;
}

export async function fetchSongRelated(videoId: string): Promise<RelatedSection[]> {
  const response = await fetch(`/api/songs/${videoId}/related`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to fetch related content");
  }

  return response.json() as Promise<RelatedSection[]>;
}
