export interface DistrictProperties {
  leaid: string;
  district_name: string;
  state: string;
  metro: string | null;
  enrollment: number | null;
  locale_code: number | null;

  // Education
  education_score: number | null;
  score_test: number | null;
  score_spending: number | null;
  naep_composite: number | null;
  current_exp_per_pupil: number | null;

  // Housing
  zhvi_sqft: number | null;
  zori_rent: number | null;
  housing_cost_buy: number | null;
  housing_cost_rent: number | null;

  // Value scores
  value_score_buy: number | null;
  value_score_rent: number | null;
  grade_buy: string;
  grade_rent: string;
}

export interface DistrictFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: DistrictProperties;
}

export type HousingMode = "buy" | "rent";

export interface ScoreMeta {
  generated: string;
  district_count: number;
  score_ranges: {
    value_score_buy: { min: number; max: number; mean: number };
    value_score_rent: { min: number; max: number; mean: number };
  };
  states: string[];
  metros: string[];
}
