"use client";

import { useState } from "react";

export function useOptionalGeolocation() {
  const [coords, setCoords] = useState<{ latitude: string; longitude: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function request() {
    if (!navigator.geolocation) {
      setError("Geolocation is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6),
        });
      },
      () => setError("Location permission was not granted. Choose a neighborhood instead."),
    );
  }

  return { coords, error, request };
}
