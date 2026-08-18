import { clusterPins } from "../cluster";
import type { MapPin, MapViewport } from "../types";
import { loadGoogleMaps } from "./loadGoogle";
import type { MapAdapter } from "./types";

type GoogleMaps = {
  maps: {
    Map: new (el: HTMLElement, opts: Record<string, unknown>) => GoogleMap;
    OverlayView: new () => GoogleOverlay & { setMap: (map: GoogleMap | null) => void };
    LatLngBounds: new () => { extend: (p: { lat: number; lng: number }) => void };
    ControlPosition: { RIGHT_BOTTOM: number };
  };
};

type GoogleMap = {
  setCenter: (p: { lat: number; lng: number }) => void;
  setZoom: (zoom: number) => void;
  fitBounds: (bounds: unknown) => void;
  getCenter: () => { lat: () => number; lng: () => number } | undefined;
  getZoom: () => number | undefined;
  getBounds: () =>
    | {
        getNorthEast: () => { lat: () => number; lng: () => number };
        getSouthWest: () => { lat: () => number; lng: () => number };
      }
    | undefined;
  addListener: (name: string, fn: () => void) => void;
  controls: unknown[][];
};

type GoogleOverlay = {
  onAdd: () => void;
  draw: () => void;
  onRemove: () => void;
  getPanes: () => { overlayMouseTarget: HTMLElement } | null;
  getProjection: () => { fromLatLngToDivPixel: (p: { lat: () => number; lng: () => number } | LatLike) => { x: number; y: number } | null };
  setMap: (map: GoogleMap | null) => void;
};

type LatLike = { lat: number; lng: number };

const FINDGOOD_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#f3ede3" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#6f675c" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#f3ede3" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "poi.park", stylers: [{ visibility: "on" }, { color: "#e4eadc" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#efe6d8" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#e4d3bc" }] },
  { featureType: "water", stylers: [{ color: "#d7e4ea" }] },
];

export async function createGoogleAdapter(element: HTMLElement, viewport: MapViewport): Promise<MapAdapter> {
  const key = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAP_ID;
  await loadGoogleMaps(key, mapId);
  const g = (window as unknown as GoogleMaps).maps;
  const map = new g.Map(element, {
    center: { lat: viewport.lat, lng: viewport.lng },
    zoom: viewport.zoom,
    disableDefaultUI: true,
    zoomControl: true,
    zoomControlOptions: { position: g.ControlPosition.RIGHT_BOTTOM },
    clickableIcons: false,
    gestureHandling: "greedy",
    styles: FINDGOOD_STYLE,
    mapId: mapId || undefined,
    attributionControl: true,
  });

  let idleHandler: ((next: MapViewport) => void) | null = null;
  let selectHandler: ((id: string) => void) | null = null;
  let hoverHandler: ((id: string | null) => void) | null = null;
  const overlays: Array<{ setMap: (map: GoogleMap | null) => void }> = [];
  let userDot: { setMap: (map: GoogleMap | null) => void } | null = null;

  map.addListener("idle", () => {
    if (!idleHandler) return;
    const center = map.getCenter();
    const bounds = map.getBounds();
    if (!center || !bounds) return;
    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    idleHandler({
      lat: center.lat(),
      lng: center.lng(),
      zoom: map.getZoom() ?? viewport.zoom,
      north: ne.lat(),
      south: sw.lat(),
      east: ne.lng(),
      west: sw.lng(),
    });
  });

  function clearPins() {
    while (overlays.length) {
      overlays.pop()?.setMap(null);
    }
  }

  return {
    setViewport(next) {
      map.setCenter({ lat: next.lat, lng: next.lng });
      map.setZoom(next.zoom);
    },
    fitBounds(next) {
      const box = new g.LatLngBounds();
      box.extend({ lat: next.north, lng: next.west });
      box.extend({ lat: next.south, lng: next.east });
      map.fitBounds(box);
    },
    setUserLocation(point) {
      userDot?.setMap(null);
      userDot = null;
      if (!point) return;
      userDot = makeOverlay(g, map, point.lat, point.lng, userLocationNode(), "user");
    },
    renderPins(pins, selectedId, hoveredId) {
      clearPins();
      for (const item of clusterPins(pins, map.getZoom() ?? 12)) {
        if (item.kind === "cluster") {
          const node = clusterNode(item.count);
          node.addEventListener("click", (event) => {
            event.stopPropagation();
            map.setZoom((map.getZoom() ?? 12) + 2);
            map.setCenter({ lat: item.lat, lng: item.lng });
          });
          overlays.push(makeOverlay(g, map, item.lat, item.lng, node, `cluster-${item.id}`));
          continue;
        }
        const pin = item.pin;
        const lat = Number(pin.lat);
        const lng = Number(pin.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        const selected = pin.id === selectedId;
        const hovered = pin.id === hoveredId;
        const node = dealMarkerNode(pin, selected, hovered);
        node.addEventListener("click", (event) => {
          event.stopPropagation();
          selectHandler?.(pin.id);
        });
        node.addEventListener("mouseenter", () => hoverHandler?.(pin.id));
        node.addEventListener("mouseleave", () => hoverHandler?.(null));
        overlays.push(makeOverlay(g, map, lat, lng, node, pin.id, selected));
      }
    },
    onIdle(handler) {
      idleHandler = handler;
    },
    onSelect(handler) {
      selectHandler = handler;
    },
    onHover(handler) {
      hoverHandler = handler;
    },
    destroy() {
      clearPins();
      userDot?.setMap(null);
    },
  };
}

function dealMarkerNode(pin: MapPin, selected: boolean, hovered: boolean): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `fg-marker${selected ? " is-selected" : ""}${hovered ? " is-hovered" : ""}`;
  button.setAttribute("aria-label", `${pin.name}${pin.best_offer ? `, ${pin.best_offer.label}` : ""}`);
  button.textContent = pin.best_offer?.label ?? pin.name.slice(0, 12);
  return button;
}

function clusterNode(count: number): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "fg-cluster";
  button.setAttribute("aria-label", `${count} deals in this area`);
  button.textContent = String(count);
  return button;
}

function userLocationNode(): HTMLDivElement {
  const node = document.createElement("div");
  node.className = "fg-user";
  node.setAttribute("aria-label", "Your location");
  return node;
}

function makeOverlay(
  g: GoogleMaps["maps"],
  map: GoogleMap,
  lat: number,
  lng: number,
  node: HTMLElement,
  id: string,
  selected = false,
) {
  // OverlayView is assigned as methods, not subclassed, so TypeScript
  // does not fight Google's instance-property typings.
  const overlay = new g.OverlayView();
  overlay.onAdd = () => {
    overlay.getPanes()?.overlayMouseTarget.appendChild(node);
  };
  overlay.draw = () => {
    const projection = overlay.getProjection();
    const point = projection?.fromLatLngToDivPixel({ lat: () => lat, lng: () => lng });
    if (!point) return;
    node.style.left = `${point.x}px`;
    node.style.top = `${point.y}px`;
    node.style.zIndex = selected ? "30" : "10";
  };
  overlay.onRemove = () => {
    node.remove();
  };
  overlay.setMap(map);
  void id;
  return overlay;
}
