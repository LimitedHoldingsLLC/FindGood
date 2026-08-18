type EventName =
  | "deal_impression"
  | "deal_opened"
  | "venue_opened"
  | "directions_clicked"
  | "deal_saved"
  | "deal_shared"
  | "source_reported_wrong"
  | "location_changed"
  | "map_opened"
  | "search_area_clicked"
  | "map_marker_clicked"
  | "map_filter_changed"
  | "map_location_requested"
  | "map_to_detail_conversion";

type AnalyticsAdapter = {
  track: (event: EventName, properties?: Record<string, unknown>) => void;
};

const consoleAdapter: AnalyticsAdapter = {
  track(event, properties) {
    if (process.env.NODE_ENV !== "production") {
      console.info("[analytics]", event, properties ?? {});
    }
  },
};

let adapter: AnalyticsAdapter = consoleAdapter;

export const analytics = {
  track(event: EventName, properties?: Record<string, unknown>) {
    adapter.track(event, properties);
  },
  use(next: AnalyticsAdapter) {
    adapter = next;
  },
};
