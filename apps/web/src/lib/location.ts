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
  "Silver Lake",
  "Santa Monica",
  "Los Feliz",
  "Echo Park",
];
