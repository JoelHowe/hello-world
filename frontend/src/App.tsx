import { useCallback, useEffect, useState } from "react";
import { api, TrendingLink, Viewer } from "./api";
import { Header } from "./components/Header";
import { LinkCard } from "./components/LinkCard";
import { LoginForm } from "./components/LoginForm";

export function App() {
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [links, setLinks] = useState<TrendingLink[]>([]);
  const [loadingLinks, setLoadingLinks] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reloadTrending = useCallback(async () => {
    setLoadingLinks(true);
    try {
      const [t, lr] = await Promise.all([api.trending(), api.lastRefresh()]);
      setLinks(t);
      setLastRefreshedAt(lr.last_refreshed_at);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingLinks(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const v = await api.me();
        setViewer(v);
        if (v) await reloadTrending();
      } finally {
        setBootstrapping(false);
      }
    })();
  }, [reloadTrending]);

  const onLogin = useCallback(
    async (v: Viewer) => {
      setViewer(v);
      await reloadTrending();
    },
    [reloadTrending],
  );

  const onRefresh = useCallback(async () => {
    setError(null);
    setRefreshing(true);
    try {
      await api.refresh();
      await reloadTrending();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }, [reloadTrending]);

  const onLogout = useCallback(async () => {
    await api.logout();
    setViewer(null);
    setLinks([]);
    setLastRefreshedAt(null);
  }, []);

  if (bootstrapping) {
    return <div className="app"><p className="meta">Loading…</p></div>;
  }

  return (
    <div className="app">
      <Header
        viewer={viewer}
        lastRefreshedAt={lastRefreshedAt}
        refreshing={refreshing}
        onRefresh={onRefresh}
        onLogout={onLogout}
      />

      {!viewer && <LoginForm onLogin={onLogin} />}

      {viewer && error && <div className="error">{error}</div>}

      {viewer && !error && links.length === 0 && !loadingLinks && (
        <div className="empty">
          {lastRefreshedAt ? (
            <>
              No links shared by two or more of your follows in the last 24 hours.
              <br />
              Try again later, or follow more people.
            </>
          ) : (
            <>
              No data yet. Click <b>Refresh</b> to pull your last 24 hours of
              timeline.
            </>
          )}
        </div>
      )}

      {viewer && links.length > 0 && (
        <div className="card-list">
          {links.map((link) => (
            <LinkCard key={link.canonical_url} link={link} />
          ))}
        </div>
      )}

      <div className="footer-note">
        Reads your Bluesky home timeline, groups URLs by canonical form, shows
        those shared by 2+ accounts you follow in the last 24 hours.
      </div>
    </div>
  );
}
