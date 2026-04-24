import { Sharer } from "../api";

type Props = { sharers: Sharer[]; max?: number };

export function SharerAvatars({ sharers, max = 5 }: Props) {
  const shown = sharers.slice(0, max);
  return (
    <span className="sharer-avatars" aria-hidden>
      {shown.map((s) =>
        s.avatar_url ? (
          <img
            key={s.handle}
            src={s.avatar_url}
            alt={s.display_name ?? s.handle}
            title={`@${s.handle}`}
            loading="lazy"
          />
        ) : (
          <span
            key={s.handle}
            className="placeholder"
            title={`@${s.handle}`}
          />
        ),
      )}
    </span>
  );
}
