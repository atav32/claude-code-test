"use client";

const LEGEND_ITEMS = [
  { color: "#15803d", label: "9–10  Excellent value" },
  { color: "#22c55e", label: "7–8.9  Great value" },
  { color: "#86efac", label: "5.5–6.9  Good value" },
  { color: "#fde68a", label: "4.5–5.4  Average" },
  { color: "#f97316", label: "3–4.4  Below average" },
  { color: "#ef4444", label: "0–2.9  Poor value" },
  { color: "#9ca3af", label: "No data" },
];

export default function Legend() {
  return (
    <div className="absolute bottom-8 left-4 z-[1000] bg-white rounded-xl shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-2">Education Value Score</p>
      {LEGEND_ITEMS.map(({ color, label }) => (
        <div key={label} className="flex items-center gap-2 mb-1">
          <span
            className="inline-block w-4 h-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="text-gray-600">{label}</span>
        </div>
      ))}
    </div>
  );
}
