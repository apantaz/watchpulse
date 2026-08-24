import { useState } from "react";
import type { CatalogItem } from "../api/catalog";
import { ProviderLogo } from "./ProviderLogo";

const IMAGE_BASE_URL = (
  import.meta.env.VITE_TMDB_IMAGE_BASE_URL ?? "https://image.tmdb.org/t/p/w500"
).replace(/\/$/, "");

type TitleCardProps = {
  item: CatalogItem;
  rank?: number;
};

function safeWatchUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function TitleCard({ item, rank }: TitleCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const posterUrl = item.poster_path && !imageFailed
    ? `${IMAGE_BASE_URL}/${item.poster_path.replace(/^\//, "")}`
    : null;
  const providers = [...new Map(
    item.availabilities.map((availability) => [availability.provider_key, availability]),
  ).values()];
  const tmdbUrl = `https://www.themoviedb.org/${item.content_type === "tv" ? "tv" : "movie"}/${item.tmdb_id}`;
  const genreLabel = item.genre_names.slice(0, 2).join(" · ");

  return (
    <article className="title-card" aria-label={rank ? `Number ${rank}: ${item.title}` : item.title}>
      {rank && <span className="rank" aria-hidden="true">{rank}</span>}
      <a
        className="poster-frame"
        href={tmdbUrl}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`View ${item.title} on TMDB`}
      >
        {posterUrl ? (
          <img src={posterUrl} alt={`Poster for ${item.title}`} loading="lazy" onError={() => setImageFailed(true)} />
        ) : (
          <div className="poster-fallback" role="img" aria-label={`No poster available for ${item.title}`}>
            <span>{item.title.slice(0, 1)}</span>
          </div>
        )}
        {item.overview && (
          <span className="poster-description" aria-hidden="true">
            <span>{item.overview}</span>
          </span>
        )}
        {item.tmdb_rating !== null && <span className="rating">★ {item.tmdb_rating.toFixed(1)}</span>}
      </a>
      <div className="card-copy">
        <h3>{item.title}</h3>
        <p>
          {[item.release_year, item.content_type === "tv" ? "Series" : "Movie", item.runtime_minutes ? `${item.runtime_minutes} min` : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {genreLabel && <p className="card-genres">{genreLabel}</p>}
        <div className="provider-badges" aria-label={`Available on ${providers.map(({ provider_name }) => provider_name).join(", ")}`}>
          {providers.slice(0, 2).map((availability) => {
            const watchUrl = safeWatchUrl(availability.watch_url);
            const contents = (
              <>
                <ProviderLogo providerKey={availability.provider_key} providerName={availability.provider_name} decorative />
                {availability.provider_name}
                {watchUrl && <span aria-hidden="true">↗</span>}
              </>
            );
            return watchUrl ? (
              <a
                className="provider-badge linked"
                href={watchUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Open ${item.title} on ${availability.provider_name}`}
                key={availability.provider_key}
              >
                {contents}
              </a>
            ) : (
              <span
                className="provider-badge unavailable"
                title="Direct link unavailable"
                aria-label={`${availability.provider_name}; direct link unavailable`}
                key={availability.provider_key}
              >
                {contents}
              </span>
            );
          })}
          {providers.length > 2 && <span className="provider-more">+{providers.length - 2}</span>}
        </div>
      </div>
    </article>
  );
}
