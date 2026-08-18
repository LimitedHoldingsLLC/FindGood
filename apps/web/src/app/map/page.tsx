import type { Metadata } from "next";

import { MapExperience } from "@/features/map/MapExperience";
import { filtersFromSearch, viewportFromSearch, type MapSearch } from "@/features/map/query";

export const metadata: Metadata = {
  title: "Map",
  description: "See where good food and drink deals are around Los Angeles.",
  robots: { index: false, follow: true },
};

export default async function MapPage({ searchParams }: { searchParams: Promise<MapSearch> }) {
  const params = await searchParams;
  return <MapExperience initialViewport={viewportFromSearch(params)} initialFilters={filtersFromSearch(params)} />;
}
