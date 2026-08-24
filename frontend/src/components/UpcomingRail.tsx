import { getUpcoming } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { CatalogRail } from "./CatalogRail";

type UpcomingRailProps = {
  scope: CatalogScope;
  filters: GlobalFilters;
};

export function UpcomingRail({ scope, filters }: UpcomingRailProps) {
  return (
    <CatalogRail
      id="upcoming-title"
      title="Upcoming"
      loadingLabel="Loading Upcoming"
      emptyTitle="No upcoming titles match these filters."
      emptyHint="Upcoming availability depends on announcements from your selected providers."
      errorFallback="Unable to load Upcoming"
      scope={scope}
      filters={filters}
      load={getUpcoming}
      lifecycleDate="available_from"
    />
  );
}
