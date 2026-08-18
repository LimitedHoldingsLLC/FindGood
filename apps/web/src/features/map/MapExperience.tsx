"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { analytics } from "@/lib/analytics";
import { api } from "@/lib/api/client";
import { useOptionalGeolocation } from "@/hooks/use-optional-geolocation";

import { MapFilters } from "./MapFilters";
import { MobileSheet } from "./MobileSheet";
import { ResultCard } from "./ResultCard";
import { apiQueryFromState, hasActiveMapFilters, mapHref } from "./query";
import type { MapFilters as Filters, MapList, MapPin, MapViewport } from "./types";

const MapCanvas = dynamic(() => import("./MapCanvas").then((mod) => mod.MapCanvas), { ssr: false });

export function MapExperience({
  initialViewport,
  initialFilters,
}: {
  initialViewport: MapViewport;
  initialFilters: Filters;
}) {
  const router = useRouter();
  const geo = useOptionalGeolocation();
  const [viewport, setViewport] = useState(initialViewport);
  const [queryViewport, setQueryViewport] = useState(initialViewport);
  const [filters, setFilters] = useState(initialFilters);
  const [results, setResults] = useState<MapList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapFailed, setMapFailed] = useState(!process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [searchArea, setSearchArea] = useState(false);
  const [sheet, setSheet] = useState<"peek" | "half" | "expanded">("half");
  const requestId = useRef(0);
  const skipIdle = useRef(true);

  const query = useMemo(() => apiQueryFromState(queryViewport, filters), [queryViewport, filters]);

  useEffect(() => {
    analytics.track("map_opened", { zoom: initialViewport.zoom });
  }, [initialViewport.zoom]);

  useEffect(() => {
    const id = ++requestId.current;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void api
      .listMapLocations({ ...query }, { signal: controller.signal })
      .then((payload) => {
        if (id !== requestId.current) return;
        setResults(payload);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (controller.signal.aborted || id !== requestId.current) return;
        setError(err.message);
        setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, [query]);

  const replaceUrl = useCallback(
    (nextViewport: MapViewport, nextFilters: Filters) => {
      router.replace(mapHref(nextViewport, nextFilters), { scroll: false });
    },
    [router],
  );

  function applyFilters(next: Partial<Filters>) {
    const merged = { ...filters, ...next };
    setFilters(merged);
    setSearchArea(false);
    replaceUrl(queryViewport, merged);
    analytics.track("map_filter_changed", next);
  }

  function searchNow(nextViewport = viewport) {
    setQueryViewport(nextViewport);
    setSearchArea(false);
    replaceUrl(nextViewport, filters);
    analytics.track("search_area_clicked", { zoom: nextViewport.zoom });
  }

  function onIdle(next: MapViewport) {
    setViewport(next);
    if (skipIdle.current) {
      skipIdle.current = false;
      return;
    }
    const moved =
      Math.abs(next.lat - queryViewport.lat) > 0.008 ||
      Math.abs(next.lng - queryViewport.lng) > 0.008 ||
      Math.abs(next.zoom - queryViewport.zoom) >= 1;
    if (moved) setSearchArea(true);
  }

  function selectPin(id: string) {
    setSelectedId(id);
    document.getElementById(`map-card-${id}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    analytics.track("map_marker_clicked", { id });
  }

  const pins: MapPin[] = results?.items ?? [];
  const userLocation = geo.coords
    ? { lat: Number(geo.coords.latitude), lng: Number(geo.coords.longitude) }
    : null;

  const list = (
    <div className="space-y-3">
      {loading ? <p className="text-sm text-muted">Searching this area…</p> : null}
      {error ? (
        <p className="text-sm text-terracotta">
          {error}. <button type="button" className="underline" onClick={() => searchNow()}>Retry</button>
        </p>
      ) : null}
      {!loading && pins.length === 0 ? (
        <p className="text-sm text-muted">
          No verified deals here yet. Move the map or widen your filters.
          {hasActiveMapFilters(filters) ? (
            <button type="button" className="ml-2 underline" onClick={() => applyFilters({ q: undefined, when: undefined, offering: undefined, dealType: undefined, cuisine: undefined, price: undefined })}>
              Clear filters
            </button>
          ) : null}
        </p>
      ) : null}
      {results?.zoom_required ? (
        <p className="text-sm text-muted">Zoom in to see every deal in this area.</p>
      ) : null}
      {pins.map((pin) => (
        <ResultCard
          key={pin.id}
          pin={pin}
          selected={selectedId === pin.id}
          hovered={hoveredId === pin.id}
          returnHref={mapHref(queryViewport, filters)}
          onSelect={() => selectPin(pin.id)}
          onHover={(on) => setHoveredId(on ? pin.id : null)}
        />
      ))}
    </div>
  );

  return (
    <div className="relative h-[calc(100dvh-4.25rem)] overflow-hidden">
      <div className="absolute inset-0 md:left-[38%]">
        {mapFailed ? (
          <div className="flex h-full items-center justify-center bg-card px-6 text-center text-sm text-muted">
            The map basemap is unavailable. Browse the deal list instead. Add a browser Maps key to enable the map.
          </div>
        ) : (
          <MapCanvas
            viewport={initialViewport}
            pins={pins}
            selectedId={selectedId}
            hoveredId={hoveredId}
            userLocation={userLocation}
            onIdle={onIdle}
            onSelect={selectPin}
            onHover={setHoveredId}
            onReady={() => setMapFailed(false)}
            onFailed={() => setMapFailed(true)}
          />
        )}
        {searchArea ? (
          <button
            type="button"
            className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-full bg-ink px-4 py-2 text-sm text-paper shadow-card"
            onClick={() => searchNow()}
          >
            Search this area
          </button>
        ) : null}
      </div>

      <aside className="relative z-10 hidden h-full w-[38%] flex-col border-r border-ink/10 bg-paper/95 p-4 backdrop-blur md:flex">
        <MapFilters
          filters={filters}
          onChange={applyFilters}
          onSearch={(q) => applyFilters({ q })}
        />
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            className="rounded-full border border-ink/15 px-3 py-1.5 text-sm"
            onClick={() => {
              geo.request();
              analytics.track("map_location_requested", {});
            }}
          >
            Use my location
          </button>
        </div>
        {geo.error ? <p className="mt-2 text-xs text-muted">{geo.error}</p> : null}
        <div className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1">{list}</div>
      </aside>

      <div className="absolute left-3 right-3 top-3 z-20 md:hidden">
        <div className="rounded-3xl border border-ink/10 bg-paper/95 p-3 shadow-card backdrop-blur">
          <MapFilters filters={filters} onChange={applyFilters} onSearch={(q) => applyFilters({ q })} />
          <button type="button" className="mt-2 text-sm text-terracotta" onClick={() => geo.request()}>
            Use my location
          </button>
        </div>
      </div>
      <MobileSheet height={sheet} onHeight={setSheet}>
        {list}
      </MobileSheet>
    </div>
  );
}
