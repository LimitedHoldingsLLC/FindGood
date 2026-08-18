import type { MapPin, MapViewport } from "../types";

export type MarkerHandle = {
  id: string;
  setSelected: (on: boolean) => void;
  setHovered: (on: boolean) => void;
};

export type MapAdapter = {
  setViewport: (viewport: MapViewport) => void;
  fitBounds: (viewport: Pick<MapViewport, "north" | "south" | "east" | "west">) => void;
  setUserLocation: (point: { lat: number; lng: number } | null) => void;
  renderPins: (pins: MapPin[], selectedId: string | null, hoveredId: string | null) => void;
  onIdle: (handler: (viewport: MapViewport) => void) => void;
  onSelect: (handler: (id: string) => void) => void;
  onHover: (handler: (id: string | null) => void) => void;
  destroy: () => void;
};
