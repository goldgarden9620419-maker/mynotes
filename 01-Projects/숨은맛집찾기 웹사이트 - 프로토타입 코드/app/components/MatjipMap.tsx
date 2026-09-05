"use client";

import { useEffect } from "react";
import { APIProvider, Map, Marker, useMap } from "@vis.gl/react-google-maps";

type MapPlace = {
  id: string;
  name: string;
  lat: number;
  lng: number;
};

function FitBounds({
  center,
  places,
}: Readonly<{ center: { lat: number; lng: number }; places: MapPlace[] }>) {
  const map = useMap();

  useEffect(() => {
    if (!map || typeof window === "undefined" || !window.google) return;
    const bounds = new window.google.maps.LatLngBounds();
    bounds.extend(center);
    places.forEach((p) => bounds.extend({ lat: p.lat, lng: p.lng }));
    map.fitBounds(bounds, 48);
  }, [map, center, places]);

  return null;
}

export default function MatjipMap({
  center,
  places,
}: Readonly<{ center: { lat: number; lng: number }; places: MapPlace[] }>) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_PLACES_API_KEY;

  if (!apiKey) return null;

  return (
    <div className="mb-4 h-64 w-full overflow-hidden rounded-2xl border border-border shadow-sm">
      <APIProvider apiKey={apiKey}>
        <Map
          defaultCenter={center}
          defaultZoom={15}
          gestureHandling="greedy"
          disableDefaultUI={false}
          fullscreenControl={false}
          streetViewControl={false}
          mapTypeControl={false}
        >
          <FitBounds center={center} places={places} />
          <Marker
            position={center}
            title="내 위치"
            icon={{
              path: 0, // google.maps.SymbolPath.CIRCLE
              scale: 8,
              fillColor: "#2563eb",
              fillOpacity: 1,
              strokeColor: "#ffffff",
              strokeWeight: 2,
            }}
            zIndex={999}
          />
          {places.map((p) => (
            <Marker key={p.id} position={{ lat: p.lat, lng: p.lng }} title={p.name} />
          ))}
        </Map>
      </APIProvider>
    </div>
  );
}
