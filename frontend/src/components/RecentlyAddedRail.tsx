import { getRecentlyAdded } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { CatalogRail } from "./CatalogRail";

type RecentlyAddedRailProps = {
  scope: CatalogScope;
  filters: GlobalFilters;
};

export function RecentlyAddedRail({ scope, filters }: RecentlyAddedRailProps) {
  return (
    <CatalogRail
      id="recently-added-title"
      title="Recently Added"
      loadingLabel="Loading Recently Added"
      emptyTitle="No recently added titles match these filters."
      emptyHint="Try another provider or remove one of the active filters."
      errorFallback="Unable to load Recently Added"
      scope={scope}
      filters={filters}
      load={getRecentlyAdded}
      lifecycleDate="available_since"
    />
  );
}
