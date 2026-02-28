"use client";

import { DistrictProperties, HousingMode } from "@/lib/types";
import {
  fmt, fmtCurrency, fmtNumber,
  getGrade, getValueScore, localeLabel, scoreColor,
} from "@/lib/utils";

interface SidebarProps {
  district: DistrictProperties | null;
  mode: HousingMode;
  onClose: () => void;
}

function ScoreBar({ label, value, tooltip }: { label: string; value: number | null; tooltip?: string }) {
  const pct = value ?? 0;
  return (
    <div className="mb-2" title={tooltip}>
      <div className="flex justify-between text-xs text-gray-500 mb-0.5">
        <span>{label}</span>
        <span className="font-mono">{fmt(value)}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: scoreColor(pct / 10) }}
        />
      </div>
    </div>
  );
}

export default function Sidebar({ district: d, mode, onClose }: SidebarProps) {
  if (!d) return null;

  const valueScore = getValueScore(d, mode);
  const grade = getGrade(d, mode);
  const color = scoreColor(valueScore);

  return (
    <aside className="absolute top-0 right-0 h-full w-80 bg-white shadow-xl z-[1000] flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b">
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-gray-900 truncate text-sm leading-tight">
            {d.district_name || "Unknown District"}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {d.state}{d.metro ? ` · ${d.metro}` : ""}
          </p>
        </div>
        <button
          onClick={onClose}
          className="ml-2 p-1 text-gray-400 hover:text-gray-600 rounded"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Value score hero */}
      <div className="p-4 flex items-center gap-4 border-b">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-xl shadow"
          style={{ backgroundColor: color }}
        >
          {grade}
        </div>
        <div>
          <div className="text-3xl font-bold text-gray-900">
            {valueScore !== null ? valueScore.toFixed(1) : "—"}
            <span className="text-sm text-gray-400 font-normal"> / 10</span>
          </div>
          <div className="text-xs text-gray-500">
            Education Value Score ({mode === "buy" ? "For Sale" : "Rental"})
          </div>
        </div>
      </div>

      {/* Score breakdown */}
      <div className="p-4 border-b">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Score Breakdown
        </h3>
        <ScoreBar
          label="Education Quality"
          value={d.education_score}
          tooltip="Composite of test scores (70%) and per-pupil spending (30%)"
        />
        <div className="pl-3 mb-2">
          <ScoreBar
            label="↳ Test Scores (NAEP)"
            value={d.score_test}
            tooltip="NAEP reading + math, grades 4 & 8, normalized nationally"
          />
          <ScoreBar
            label="↳ Per-Pupil Spending"
            value={d.score_spending}
            tooltip="Current expenditure per pupil (log-scaled), normalized nationally"
          />
        </div>
        <ScoreBar
          label={`Housing Cost (${mode === "buy" ? "$/sqft" : "median rent"})`}
          value={mode === "buy" ? d.housing_cost_buy : d.housing_cost_rent}
          tooltip="Normalized within metro area. Lower cost = lower bar = better value"
        />
        <p className="text-xs text-gray-400 mt-2">
          All scores 0–100 (percentile within comparison group)
        </p>
      </div>

      {/* Raw data */}
      <div className="p-4 border-b">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Key Stats
        </h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Enrollment</dt>
          <dd className="text-gray-900 font-medium">{fmtNumber(d.enrollment)}</dd>

          <dt className="text-gray-500">Type</dt>
          <dd className="text-gray-900 font-medium">{localeLabel(d.locale_code)}</dd>

          <dt className="text-gray-500">NAEP Score</dt>
          <dd className="text-gray-900 font-medium">{fmt(d.naep_composite)} <span className="text-xs text-gray-400">(state avg)</span></dd>

          <dt className="text-gray-500">Per-Pupil $</dt>
          <dd className="text-gray-900 font-medium">{fmtCurrency(d.current_exp_per_pupil)}</dd>

          {mode === "buy" ? (
            <>
              <dt className="text-gray-500">ZHVI $/sqft</dt>
              <dd className="text-gray-900 font-medium">{fmtCurrency(d.zhvi_sqft)}</dd>
            </>
          ) : (
            <>
              <dt className="text-gray-500">Median Rent</dt>
              <dd className="text-gray-900 font-medium">{fmtCurrency(d.zori_rent)}/mo</dd>
            </>
          )}
        </dl>
      </div>

      {/* Data sources */}
      <div className="p-4 mt-auto">
        <p className="text-xs text-gray-400 leading-relaxed">
          Education data: NCES CCD + NAEP (2022). Housing data: Zillow Research (ZHVI/ZORI).
          NAEP scores are state-level averages applied to all districts in that state
          (except select urban districts with direct NAEP sampling).
        </p>
      </div>
    </aside>
  );
}
