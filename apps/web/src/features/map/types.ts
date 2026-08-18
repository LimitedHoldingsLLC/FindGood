export type MapBounds = {
  north: number;
  south: number;
  east: number;
  west: number;
};

export type MapViewport = MapBounds & {
  lat: number;
  lng: number;
  zoom: number;
};

export type MapOffer = {
  id: string;
  label: string;
  title: string;
  freshness: string;
  availability_status: string;
  availability_label: string;
  extra_offer_count: number;
};

export type MapPin = {
  id: string;
  venue_id: string;
  slug: string;
  name: string;
  lat: string;
  lng: string;
  neighborhood: string | null;
  category: string;
  location_confidence: string;
  best_offer: MapOffer | null;
};

export type MapList = {
  items: MapPin[];
  result_count: number;
  truncated: boolean;
  zoom_required: boolean;
  cache_hit?: boolean;
};

export type MapFilters = {
  q?: string;
  when?: string;
  offering?: string;
  dealType?: string;
  cuisine?: string;
  price?: string;
};

export type MapQuery = MapFilters & {
  north: string;
  south: string;
  east: string;
  west: string;
  zoom: string;
};
