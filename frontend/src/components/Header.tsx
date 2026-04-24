import { Viewer } from "../api";
import { relativeTime } from "../time";

type Props = {
  viewer: Viewer | null;
  lastRefreshedAt: string | null;
  refreshing: boolean;
  onRefresh: () => void;
  onLogout: () => void;
};

export function Header({ viewer, lastRefreshedAt, refreshing, onRefresh, onLogout }: Props) {
  return (
    <header className="header">
      <div className="brand">
        Nuzzle Clone
        <span className="source">· Bluesky</span>
      </div>
      <div className="header-right">
        {lastRefreshedAt && (
          <span className="meta">Updated {relativeTime(lastRefreshedAt)}</span>
        )}
        {viewer && (
          <>
            <button
              className="button primary"
              onClick={onRefresh}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <span className="viewer" title={`@${viewer.handle}`}>
              {viewer.avatar_url && <img src={viewer.avatar_url} alt="" />}
              <span>@{viewer.handle}</span>
            </span>
            <button className="button" onClick={onLogout}>
              Log out
            </button>
          </>
        )}
      </div>
    </header>
  );
}
