import { getNewReleases } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { CatalogRail } from "./CatalogRail";

type NewReleasesRailProps = {
  scope: CatalogScope;
  filters: GlobalFilters;
};

export function NewReleasesRail({ scope, filters }: NewReleasesRailProps) {
  return (
    <CatalogRail
      id="new-releases-title"
      title="New Releases"
      subtitle="Recently released movies and series"
      loadingLabel="Loading New Releases"
      emptyTitle="No recent releases match these filters."
      emptyHint="Try widening the year, genre, runtime, or rating filters."
      errorFallback="Unable to load New Releases"
      scope={scope}
      filters={filters}
      load={getNewReleases}
    />
  );
}
