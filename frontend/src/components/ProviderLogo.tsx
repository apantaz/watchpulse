import { useState } from "react";

const PROVIDER_IMAGE_BASE_URL = (
  import.meta.env.VITE_TMDB_PROVIDER_IMAGE_BASE_URL ?? "https://image.tmdb.org/t/p/w92"
).replace(/\/$/, "");

// Temporary launch-provider adapter. This moves to dim_provider.logo_path when
// provider reference ingestion is delivered; unknown providers degrade safely.
const LOGO_PATHS: Record<string, string> = {
  netflix: "/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg",
  disney_plus: "/97yvRBw1GzX7fXprcF80er19ot.jpg",
  prime_video: "/pvske1MyAoymrs5bguRfVqYiM9a.jpg",
  apple_tv_plus: "/2E03IAZsX4ZaUqM7tXlctEPMGWS.jpg",
};

type ProviderLogoProps = {
  providerKey: string;
  providerName: string;
  decorative?: boolean;
};

export function ProviderLogo({ providerKey, providerName, decorative = false }: ProviderLogoProps) {
  const [failed, setFailed] = useState(false);
  const logoPath = LOGO_PATHS[providerKey];

  if (!logoPath || failed) {
    return <span className="provider-logo-fallback" aria-hidden="true">{providerName.slice(0, 1)}</span>;
  }

  return (
    <img
      className="provider-logo-image"
      src={`${PROVIDER_IMAGE_BASE_URL}${logoPath}`}
      alt={decorative ? "" : `${providerName} logo`}
      aria-hidden={decorative || undefined}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
