import type { MapPin } from "./types";

export type ClusterItem =
  | { kind: "pin"; pin: MapPin }
  | { kind: "cluster"; id: string; lat: number; lng: number; count: number; pins: MapPin[] };

// Client-side grid clustering. At FindGood's current density this is enough.
// Reconsider server clustering if a single viewport regularly returns the cap
// and users still cannot separate businesses after zooming in.
export function clusterPins(pins: MapPin[], zoom: number): ClusterItem[] {
  if (zoom >= 15 || pins.length <= 18) {
    return pins.map((pin) => ({ kind: "pin", pin }));
  }
  const cell = zoom >= 13 ? 0.008 : 0.02;
  const buckets = new Map<string, MapPin[]>();
  for (const pin of pins) {
    const lat = Number(pin.lat);
    const lng = Number(pin.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
    const key = `${Math.round(lat / cell)}:${Math.round(lng / cell)}`;
    const list = buckets.get(key) ?? [];
    list.push(pin);
    buckets.set(key, list);
  }
  const items: ClusterItem[] = [];
  for (const [key, group] of buckets) {
    if (group.length === 1) {
      items.push({ kind: "pin", pin: group[0] });
      continue;
    }
    const lat = group.reduce((sum, pin) => sum + Number(pin.lat), 0) / group.length;
    const lng = group.reduce((sum, pin) => sum + Number(pin.lng), 0) / group.length;
    items.push({ kind: "cluster", id: `cluster-${key}`, lat, lng, count: group.length, pins: group });
  }
  return items;
}
