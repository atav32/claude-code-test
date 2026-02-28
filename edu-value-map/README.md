# EduValue Map

Interactive map showing the best K–12 education quality per housing dollar, by school district.

## How it works

1. **Python pipeline** fetches public data, computes a value score per district, and exports GeoJSON
2. **Next.js frontend** loads the GeoJSON and renders an interactive choropleth map

### Scoring model

| Component | Weight | Source |
|---|---|---|
| NAEP test scores (reading + math, grades 4 & 8) | 70% | NCES / Nation's Report Card |
| Per-pupil spending (log-scaled) | 30% | NCES CCD F-33 |
| Housing cost (for-sale) | — | Zillow ZHVI $/sqft by ZIP |
| Housing cost (rental) | — | Zillow ZORI median rent by ZIP |

**Value Score** = Education Quality Score (0–100) minus Housing Cost Index (0–100, within-metro normalized), then rescaled 0–10.

## Quick start

### 1. Run the data pipeline

```bash
pip install -r pipeline/requirements.txt
python pipeline/run_pipeline.py
```

This downloads ~500 MB of public data, processes it, and writes:
- `web/public/data/districts.geojson`
- `web/public/data/districts-meta.json`

Expect ~10–20 minutes on first run. Subsequent runs use cached downloads.

### 2. Start the frontend

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Data sources

| Dataset | Provider | URL |
|---|---|---|
| CCD F-33 (per-pupil spending) | NCES | https://nces.ed.gov/ccd/ |
| CCD Directory (enrollment, locale) | NCES | https://nces.ed.gov/ccd/ |
| NAEP scores | NCES | https://www.nationsreportcard.gov/ |
| District boundaries (shapefiles) | NCES EDGE | https://nces.ed.gov/programs/edge/ |
| ZHVI $/sqft by ZIP | Zillow Research | https://www.zillow.com/research/data/ |
| ZORI rent by ZIP | Zillow Research | https://www.zillow.com/research/data/ |
| ZIP → School District crosswalk | HUD USPS | https://www.huduser.gov/portal/datasets/usps_crosswalk.html |

All data is publicly available and free to use.

## Pipeline steps

```
fetch_nces.py    → CCD finance, CCD directory, NAEP scores, NCES boundary shapefiles
fetch_zillow.py  → Zillow ZHVI sqft, Zillow ZORI rent (by ZIP)
crosswalk.py     → HUD ZIP→district crosswalk; aggregate Zillow data to district level
score.py         → Build master dataset, compute education + value scores
export.py        → Join with boundaries, write GeoJSON for the frontend
```

Run individual steps:
```bash
python pipeline/run_pipeline.py --steps fetch
python pipeline/run_pipeline.py --steps score,export
```

## Caveats

- **NAEP is state-level** for most districts. Only ~27 large urban districts have direct NAEP sampling (TUDA). All other districts inherit their state's average — treat this as an approximation.
- **Housing data lag**: Zillow data reflects recent market conditions; NCES finance data has a 1–2 year lag.
- **Metro normalization**: Housing cost is normalized within each metro area, so comparisons are most meaningful within a metro (not between, say, rural Nebraska and Manhattan).
- **Minimum enrollment**: Districts with fewer than 100 students are excluded to reduce noise.

## Deployment

The frontend has no backend — it reads static JSON/GeoJSON files. Deploy on:
- **Vercel**: `cd web && vercel deploy`
- **GitHub Pages**: export with `npm run build && npm run export`
- **Any static host**: copy `web/out/` after `npm run build`

> Re-run the pipeline annually (or when NCES/Zillow publish new data) and redeploy.
