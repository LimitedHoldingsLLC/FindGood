export const DEFAULT_CENTER = {
  lat: Number(process.env.NEXT_PUBLIC_MAP_DEFAULT_LAT ?? "34.0522"),
  lng: Number(process.env.NEXT_PUBLIC_MAP_DEFAULT_LNG ?? "-118.2437"),
};

export const DEFAULT_ZOOM = Number(process.env.NEXT_PUBLIC_MAP_DEFAULT_ZOOM ?? "12");

export const LA_BOUNDS = {
  north: 34.22,
  south: 33.92,
  east: -118.12,
  west: -118.52,
};
