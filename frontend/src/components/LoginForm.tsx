import { useState, FormEvent } from "react";
import { api, Viewer } from "../api";

type Props = { onLogin: (v: Viewer) => void };

export function LoginForm({ onLogin }: Props) {
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const viewer = await api.login(handle.trim(), password);
      onLogin(viewer);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <h2>Sign in with Bluesky</h2>
      <p>
        This tool surfaces URLs shared by multiple people in your Bluesky home
        timeline over the last 24 hours. Generate a dedicated{" "}
        <a
          href="https://bsky.app/settings/app-passwords"
          target="_blank"
          rel="noreferrer"
        >
          app password
        </a>
        {" "}— don't reuse your main password.
      </p>
      <form onSubmit={onSubmit}>
        <label htmlFor="handle">Handle</label>
        <input
          id="handle"
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          placeholder="alice.bsky.social"
          autoComplete="username"
          required
        />
        <label htmlFor="password">App password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="xxxx-xxxx-xxxx-xxxx"
          autoComplete="current-password"
          required
        />
        <button className="button primary" disabled={busy || !handle || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}
