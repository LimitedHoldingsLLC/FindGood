let loading: Promise<void> | null = null;

export function loadGoogleMaps(apiKey: string, mapId?: string): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("No window"));
  const google = (window as Window & { google?: { maps?: unknown } }).google;
  if (google?.maps) return Promise.resolve();
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    const params = new URLSearchParams({
      key: apiKey,
      v: "weekly",
    });
    if (mapId) params.set("map_ids", mapId);
    script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
    script.async = true;
    script.onerror = () => reject(new Error("Google Maps failed to load"));
    script.onload = () => resolve();
    document.head.appendChild(script);
  });
  return loading;
}
