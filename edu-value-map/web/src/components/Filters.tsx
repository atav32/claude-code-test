"use client";

import { HousingMode } from "@/lib/types";

interface FiltersProps {
  mode: HousingMode;
  onModeChange: (mode: HousingMode) => void;
  minScore: number;
  onMinScoreChange: (v: number) => void;
  stateFilter: string;
  onStateFilterChange: (s: string) => void;
  states: string[];
}

export default function Filters({
  mode,
  onModeChange,
  minScore,
  onMinScoreChange,
  stateFilter,
  onStateFilterChange,
  states,
}: FiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-3 bg-white border-b border-gray-200 shadow-sm text-sm">
      {/* Buy / Rent toggle */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
        {(["buy", "rent"] as HousingMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              mode === m
                ? "bg-white shadow text-blue-700"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {m === "buy" ? "For Sale" : "Rental"}
          </button>
        ))}
      </div>

      {/* Min value score */}
      <label className="flex items-center gap-2 text-gray-600">
        <span className="whitespace-nowrap">Min score:</span>
        <input
          type="range"
          min={0}
          max={9}
          step={0.5}
          value={minScore}
          onChange={(e) => onMinScoreChange(parseFloat(e.target.value))}
          className="w-28 accent-blue-600"
        />
        <span className="w-6 font-mono text-blue-700">{minScore}</span>
      </label>

      {/* State filter */}
      <label className="flex items-center gap-2 text-gray-600">
        <span>State:</span>
        <select
          value={stateFilter}
          onChange={(e) => onStateFilterChange(e.target.value)}
          className="border border-gray-300 rounded px-2 py-0.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">All states</option>
          {states.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
