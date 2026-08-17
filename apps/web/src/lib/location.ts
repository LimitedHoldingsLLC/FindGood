export type ConsumerLocation = {
  city: string;
  neighborhood?: string;
  latitude?: string;
  longitude?: string;
  label: string;
};

export const DEFAULT_LOCATION: ConsumerLocation = {
  city: "Los Angeles",
  label: "Los Angeles",
};

export const NEIGHBORHOODS = [
  "Downtown",
  "Arts District",
  "Koreatown",
  "Hollywood",
  "West Hollywood",
  "Silver Lake",
  "Echo Park",
  "Los Feliz",
  "Atwater Village",
  "Highland Park",
  "Eagle Rock",
  "Santa Monica",
  "Venice",
  "Culver City",
  "Studio City",
  "Pasadena",
  "Long Beach",
];
