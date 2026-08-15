export type MapProvider = {
  directionsUrl: (lat: string, lng: string, label: string) => string;
};

const nullProvider: MapProvider = {
  directionsUrl(lat, lng, label) {
    const query = encodeURIComponent(`${label} @${lat},${lng}`);
    return `https://maps.apple.com/?q=${query}`;
  },
};

let provider: MapProvider = nullProvider;

export const maps = {
  directionsUrl(lat: string, lng: string, label: string) {
    return provider.directionsUrl(lat, lng, label);
  },
  use(next: MapProvider) {
    provider = next;
  },
};
