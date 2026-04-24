export type Viewer = {
  viewer_id: string;
  source: string;
  handle: string;
  display_name: string | null;
  avatar_url: string | null;
};

export type Sharer = {
  handle: string;
  display_name: string | null;
  avatar_url: string | null;
  post_permalink: string;
  posted_at: string;
};

export type TrendingLink = {
  canonical_url: string;
  domain: string;
  title: string | null;
  description: string | null;
  image_url: string | null;
  sharer_count: number;
  sharers: Sharer[];
  most_recent_share_at: string;
  score: number;
};

export type RefreshResult = {
  posts_seen: number;
  urls_found: number;
  links_ranked: number;
  started_at: string;
  finished_at: string;
};

export type LastRefresh = {
  last_refreshed_at: string | null;
  posts_seen?: number;
  urls_found?: number;
  links_ranked?: number;
  error?: string | null;
};

async function req<T>(
  path: string,
  init?: RequestInit & { expectStatus?: number[] },
): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!resp.ok) {
    let detail = "";
    try {
      const body = await resp.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = await resp.text();
    }
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  me: () => req<Viewer | null>("/auth/me"),
  login: (handle: string, app_password: string, source = "bluesky") =>
    req<Viewer>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ handle, app_password, source }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  refresh: () => req<RefreshResult>("/refresh", { method: "POST" }),
  trending: (hours = 24, limit = 50) =>
    req<TrendingLink[]>(`/trending?hours=${hours}&limit=${limit}`),
  lastRefresh: () => req<LastRefresh>("/last-refresh"),
};
