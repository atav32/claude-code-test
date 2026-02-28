"use client";

/**
 * Choropleth map of school districts, colored by Education Value Score.
 * Uses React-Leaflet with OpenStreetMap tiles (no API key required).
 *
 * Loaded dynamically (next/dynamic with ssr:false) because Leaflet requires
 * the browser's window object.
 */

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, GeoJSON, ZoomControl } from "react-leaflet";
import type { Layer, GeoJSON as LeafletGeoJSON, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";

import { DistrictFeature, DistrictProperties, HousingMode } from "@/lib/types";
import { getValueScore, scoreColor } from "@/lib/utils";

interface MapProps {
  features: DistrictFeature[];
  mode: HousingMode;
  onDistrictClick: (props: DistrictProperties) => void;
  selectedLeaid: string | null;
}

function styleFeature(feature: DistrictFeature, mode: HousingMode, selectedLeaid: string | null): PathOptions {
  const score = getValueScore(feature.properties, mode);
  const isSelected = feature.properties.leaid === selectedLeaid;
  return {
    fillColor: scoreColor(score),
    fillOpacity: score !== null ? 0.72 : 0.2,
    color: isSelected ? "#1d4ed8" : "#6b7280",
    weight: isSelected ? 2.5 : 0.4,
    opacity: 0.8,
  };
}

export default function Map({ features, mode, onDistrictClick, selectedLeaid }: MapProps) {
  const geoJsonRef = useRef<LeafletGeoJSON | null>(null);

  // Re-style all features when mode or selection changes
  useEffect(() => {
    if (!geoJsonRef.current) return;
    geoJsonRef.current.eachLayer((layer: Layer) => {
      const gl = layer as LeafletGeoJSON & { feature?: DistrictFeature };
      if (gl.feature && "setStyle" in gl) {
        (gl as any).setStyle(styleFeature(gl.feature as DistrictFeature, mode, selectedLeaid));
      }
    });
  }, [mode, selectedLeaid]);

  if (features.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center text-gray-500">
          <div className="text-4xl mb-2">🗺️</div>
          <p className="font-medium">No map data loaded</p>
          <p className="text-sm mt-1">
            Run the pipeline to generate{" "}
            <code className="bg-gray-100 px-1 rounded">web/public/data/districts.geojson</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <MapContainer
      center={[38.5, -96]}
      zoom={4}
      className="flex-1 h-full w-full"
      zoomControl={false}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        opacity={0.6}
      />
      <ZoomControl position="bottomright" />
      <GeoJSON
        key={`${features.length}-${mode}`}  // remount when data changes
        ref={geoJsonRef}
        data={{ type: "FeatureCollection", features } as GeoJSON.FeatureCollection}
        style={(feature) =>
          styleFeature(feature as DistrictFeature, mode, selectedLeaid)
        }
        onEachFeature={(feature, layer) => {
          const f = feature as DistrictFeature;
          layer.on({
            click: () => onDistrictClick(f.properties),
            mouseover: (e) => {
              const l = e.target as any;
              l.setStyle({ weight: 2, color: "#1d4ed8", fillOpacity: 0.85 });
              l.bringToFront();
            },
            mouseout: (e) => {
              const l = e.target as any;
              l.setStyle(styleFeature(f, mode, selectedLeaid));
            },
          });
        }}
      />
    </MapContainer>
  );
}
