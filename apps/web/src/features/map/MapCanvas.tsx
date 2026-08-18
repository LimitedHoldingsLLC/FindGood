"use client";

import { useEffect, useRef } from "react";

import { createGoogleAdapter } from "./adapter/google";
import type { MapAdapter } from "./adapter/types";
import type { MapPin, MapViewport } from "./types";

export function MapCanvas({
  viewport,
  pins,
  selectedId,
  hoveredId,
  userLocation,
  onIdle,
  onSelect,
  onHover,
  onReady,
  onFailed,
}: {
  viewport: MapViewport;
  pins: MapPin[];
  selectedId: string | null;
  hoveredId: string | null;
  userLocation: { lat: number; lng: number } | null;
  onIdle: (next: MapViewport) => void;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onReady: () => void;
  onFailed: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const adapter = useRef<MapAdapter | null>(null);
  const idle = useRef(onIdle);
  const select = useRef(onSelect);
  const hover = useRef(onHover);
  idle.current = onIdle;
  select.current = onSelect;
  hover.current = onHover;

  useEffect(() => {
    const element = host.current;
    if (!element || !process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY) {
      onFailed();
      return;
    }
    let cancelled = false;
    void createGoogleAdapter(element, viewport)
      .then((next) => {
        if (cancelled) {
          next.destroy();
          return;
        }
        adapter.current = next;
        next.onIdle((value) => idle.current(value));
        next.onSelect((id) => select.current(id));
        next.onHover((id) => hover.current(id));
        onReady();
      })
      .catch(() => {
        if (!cancelled) onFailed();
      });
    return () => {
      cancelled = true;
      adapter.current?.destroy();
      adapter.current = null;
    };
    // The adapter is created once for this map instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    adapter.current?.renderPins(pins, selectedId, hoveredId);
  }, [pins, selectedId, hoveredId]);

  useEffect(() => {
    adapter.current?.setUserLocation(userLocation);
  }, [userLocation]);

  return <div ref={host} className="absolute inset-0" role="application" aria-label="FindGood deals map" />;
}
