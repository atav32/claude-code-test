import { DistrictProperties, HousingMode } from "./types";

/** Return the value score for the current housing mode. */
export function getValueScore(d: DistrictProperties, mode: HousingMode): number | null {
  return mode === "buy" ? d.value_score_buy : d.value_score_rent;
}

export function getGrade(d: DistrictProperties, mode: HousingMode): string {
  return mode === "buy" ? d.grade_buy : d.grade_rent;
}

/** Map a 0–10 value score to a Tailwind color class. */
export function scoreColor(score: number | null): string {
  if (score === null) return "#9ca3af"; // gray-400
  if (score >= 8.5) return "#15803d"; // green-700
  if (score >= 7.0) return "#22c55e"; // green-500
  if (score >= 5.5) return "#86efac"; // green-300
  if (score >= 4.5) return "#fde68a"; // yellow-200
  if (score >= 3.0) return "#f97316"; // orange-500
  return "#ef4444";                   // red-500
}

/** Locale code → human-readable label (NCES LOCALE taxonomy). */
export function localeLabel(code: number | null): string {
  if (!code) return "Unknown";
  const locale: Record<number, string> = {
    11: "City: Large",
    12: "City: Mid-size",
    13: "City: Small",
    21: "Suburb: Large",
    22: "Suburb: Mid-size",
    23: "Suburb: Small",
    31: "Town: Fringe",
    32: "Town: Distant",
    33: "Town: Remote",
    41: "Rural: Fringe",
    42: "Rural: Distant",
    43: "Rural: Remote",
  };
  return locale[code] ?? `Locale ${code}`;
}

export function fmt(n: number | null, decimals = 1): string {
  if (n === null || n === undefined) return "—";
  return n.toFixed(decimals);
}

export function fmtCurrency(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export function fmtNumber(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}
