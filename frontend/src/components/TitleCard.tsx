import { useState } from "react";
import type { CatalogItem } from "../api/catalog";
import { ProviderLogo } from "./ProviderLogo";

const IMAGE_BASE_URL = (
  import.meta.env.VITE_TMDB_IMAGE_BASE_URL ?? "https://image.tmdb.org/t/p/w500"
).replace(/\/$/, "");

type TitleCardProps = {
  item: CatalogItem;
  rank?: number;
  lifecycleDate?: "available_since" | "available_from";
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

const formatLifecycleDate = (value: string) => new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
}).format(new Date(value));

export function TitleCard({ item, rank, lifecycleDate }: TitleCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const posterUrl = item.poster_path && !imageFailed
    ? `${IMAGE_BASE_URL}/${item.poster_path.replace(/^\//, "")}`
    : null;
  const providers = [...new Map(
    item.availabilities.map((availability) => [availability.provider_key, availability]),
  ).values()];
  const tmdbUrl = `https://www.themoviedb.org/${item.content_type === "tv" ? "tv" : "movie"}/${item.tmdb_id}`;
  const genreLabel = item.genre_names.slice(0, 2).join(" · ");
  const hasRating = item.tmdb_rating !== null && item.tmdb_rating > 0;
  const lifecycleDates = lifecycleDate
    ? item.availabilities
      .map((availability) => availability[lifecycleDate])
      .filter((value): value is string => value !== null)
      .sort()
    : [];
  const lifecycleValue = lifecycleDate === "available_since"
    ? lifecycleDates.at(-1)
    : lifecycleDates.at(0);
  const hasCurrentAvailability = item.availabilities.some((availability) => availability.is_available);
  const lifecycleLabel = lifecycleDate === "available_from"
    ? item.content_type === "tv" && hasCurrentAvailability ? "New season coming" : "Coming"
    : "Added";
  const seriesDetails = item.content_type === "tv" && lifecycleDate !== "available_from"
    ? [
      item.season_count ? `${item.season_count} ${item.season_count === 1 ? "season" : "seasons"}` : null,
      item.episode_count ? `${item.episode_count} ${item.episode_count === 1 ? "episode" : "episodes"}` : null,
    ].filter(Boolean).join(" · ")
    : null;
  const formatDetail = seriesDetails || (item.runtime_minutes ? `${item.runtime_minutes} min` : null);

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
        <span className={`rating${hasRating ? "" : " unrated"}`}>
          {hasRating ? `★ ${item.tmdb_rating!.toFixed(1)}` : "N/A"}
        </span>
      </a>
      <div className="card-copy">
        <h3>{item.title}</h3>
        <p>
          {[item.release_year, item.content_type === "tv" ? "Series" : "Movie", formatDetail]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {genreLabel && <p className="card-genres">{genreLabel}</p>}
        {lifecycleValue && (
          <p className="lifecycle-date">
            {lifecycleLabel} {formatLifecycleDate(lifecycleValue)}
          </p>
        )}
        <div className="provider-badges" aria-label={`Available on ${providers.map(({ provider_name }) => provider_name).join(", ")}`}>
          {providers.map((availability) => {
            const watchUrl = safeWatchUrl(availability.watch_url);
            const contents = (
              <ProviderLogo providerKey={availability.provider_key} providerName={availability.provider_name} decorative />
            );
            return watchUrl ? (
              <a
                className="provider-badge linked"
                href={watchUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Open ${item.title} on ${availability.provider_name}`}
                data-tooltip={`Watch on ${availability.provider_name}`}
                key={availability.provider_key}
              >
                {contents}
              </a>
            ) : (
              <span
                className="provider-badge unavailable"
                data-tooltip="Available on this provider, but a direct title link is unavailable."
                aria-label={`${availability.provider_name}; direct link unavailable`}
                tabIndex={0}
                key={availability.provider_key}
              >
                {contents}
              </span>
            );
          })}
        </div>
      </div>
    </article>
  );
}
