import { TrendingLink } from "../api";
import { SharerAvatars } from "./SharerAvatars";
import { relativeTime } from "../time";

type Props = { link: TrendingLink };

export function LinkCard({ link }: Props) {
  const firstSharer = link.sharers[0];
  const others = Math.max(0, link.sharer_count - 1);
  const sharerSummary =
    others > 0
      ? `${firstSharer?.display_name ?? "@" + firstSharer?.handle} and ${others} other${others === 1 ? "" : "s"}`
      : firstSharer?.display_name ?? `@${firstSharer?.handle ?? "?"}`;

  return (
    <a
      className="card"
      href={link.canonical_url}
      target="_blank"
      rel="noreferrer noopener"
    >
      <div
        className="thumb"
        style={
          link.image_url ? { backgroundImage: `url(${cssUrl(link.image_url)})` } : undefined
        }
      />
      <div className="body">
        <span className="domain">{link.domain}</span>
        <h3 className="title">{link.title ?? link.canonical_url}</h3>
        {link.description && <p className="description">{link.description}</p>}
        <div className="sharers">
          <SharerAvatars sharers={link.sharers} />
          <span className="sharer-text">
            Shared by {sharerSummary} · {relativeTime(link.most_recent_share_at)}
          </span>
        </div>
      </div>
    </a>
  );
}

function cssUrl(url: string): string {
  return url.replace(/["\\]/g, "\\$&");
}
