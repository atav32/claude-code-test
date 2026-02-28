"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import Filters from "@/components/Filters";
import Legend from "@/components/Legend";
import Sidebar from "@/components/Sidebar";
import { DistrictFeature, DistrictProperties, HousingMode, ScoreMeta } from "@/lib/types";
import { getValueScore } from "@/lib/utils";

// Leaflet requires browser APIs — load without SSR
const Map = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-slate-50">
      <div className="text-gray-400 text-sm animate-pulse">Loading map…</div>
    </div>
  ),
});

export default function Home() {
  const [features, setFeatures] = useState<DistrictFeature[]>([]);
  const [meta, setMeta] = useState<ScoreMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mode, setMode] = useState<HousingMode>("buy");
  const [minScore, setMinScore] = useState(0);
  const [stateFilter, setStateFilter] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictProperties | null>(null);

  // Load GeoJSON + metadata
  useEffect(() => {
    async function load() {
      try {
        const [geoRes, metaRes] = await Promise.all([
          fetch("/data/districts.geojson"),
          fetch("/data/districts-meta.json"),
        ]);

        if (!geoRes.ok) throw new Error(`districts.geojson not found (${geoRes.status})`);
        const geo = await geoRes.json();
        setFeatures(geo.features ?? []);

        if (metaRes.ok) {
          setMeta(await metaRes.json());
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Filter features client-side
  const visibleFeatures = useMemo(() => {
    return features.filter((f) => {
      const score = getValueScore(f.properties, mode);
      if (score === null || score < minScore) return false;
      if (stateFilter && f.properties.state !== stateFilter) return false;
      return true;
    });
  }, [features, mode, minScore, stateFilter]);

  const states = useMemo(
    () => meta?.states ?? [...new Set(features.map((f) => f.properties.state).filter(Boolean))].sort() as string[],
    [meta, features]
  );

  return (
    <div className="flex flex-col h-screen bg-gray-50 font-sans">
      {/* Top bar */}
      <header className="px-4 py-2.5 bg-blue-700 text-white flex items-center gap-3 shadow">
        <div>
          <h1 className="font-bold text-base leading-tight">EduValue Map</h1>
          <p className="text-blue-200 text-xs">Best education quality per housing dollar</p>
        </div>
        {meta && (
          <span className="ml-auto text-xs text-blue-300">
            {meta.district_count.toLocaleString()} districts · data as of {meta.generated?.slice(0, 10)}
          </span>
        )}
      </header>

      {/* Filters bar */}
      <Filters
        mode={mode}
        onModeChange={setMode}
        minScore={minScore}
        onMinScoreChange={setMinScore}
        stateFilter={stateFilter}
        onStateFilterChange={setStateFilter}
        states={states}
      />

      {/* Map area */}
      <div className="relative flex-1 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-white/80 z-[2000] flex items-center justify-center">
            <div className="text-gray-500 text-sm animate-pulse">Loading district data…</div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-[2000]">
            <div className="bg-white rounded-xl shadow-lg p-6 max-w-md text-center">
              <div className="text-3xl mb-2">⚠️</div>
              <p className="font-semibold text-gray-800 mb-1">Map data not available</p>
              <p className="text-sm text-gray-500 mb-3">{error}</p>
              <p className="text-xs text-gray-400 bg-gray-50 rounded p-2 font-mono">
                Run: python pipeline/run_pipeline.py
              </p>
            </div>
          </div>
        )}

        <Map
          features={visibleFeatures}
          mode={mode}
          onDistrictClick={setSelectedDistrict}
          selectedLeaid={selectedDistrict?.leaid ?? null}
        />

        <Legend />

        {/* Visible count badge */}
        {visibleFeatures.length < features.length && features.length > 0 && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-white rounded-full px-3 py-1 shadow text-xs text-gray-600">
            Showing {visibleFeatures.length.toLocaleString()} of {features.length.toLocaleString()} districts
          </div>
        )}

        <Sidebar
          district={selectedDistrict}
          mode={mode}
          onClose={() => setSelectedDistrict(null)}
        />
      </div>
    </div>
  );
}
