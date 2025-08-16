# Vehicle Registration Investor Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) ![Status](https://img.shields.io/badge/status-active-success) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

Data-driven Streamlit platform delivering actionable insights from Indian vehicle registration trends (states, manufacturers, categories) with growth, volatility, market share and export capabilities.

<p align="center">
  <img src="docs/images/dashboard_preview.png" alt="Dashboard Preview" width="850"/>
</p>

## Table of Contents
1. Vision
2. Key Capabilities
3. Architecture Overview
4. Data Model & Flow
5. Tech Stack
6. Quick Start
7. Run Modes
8. Configuration & Environment
9. Usage Guide
10. Analytics Implemented
11. Exports
12. Theming (Light/Dark)
13. Testing & Quality
14. Performance Notes
15. Security & Privacy
16. Roadmap
17. Contributing
18. FAQ
19. Support
20. License

## 1. Vision
Provide investors and analysts with a lightweight, transparent and extensible analytics layer over publicly observable vehicle registration dynamics to inform growth, share, and volatility assessments.

## 2. Key Capabilities
- Multi-dimensional filtering (dates, states, manufacturers, categories)
- Growth analytics: YoY, QoQ, MoM, rolling trends
- Volatility & drawdown metrics (30-day windows)
- Market share normalization per (date, vehicle_category)
- Comparative stacked and indexed charts (Plotly)
- Data export (CSV, XLSX, PDF summary)
- Theme toggle (light/dark) with consistent UI styling
- Deterministic processing pipeline enabling unit tests

## 3. Architecture Overview
```
Streamlit UI  --->  Analytics Layer  ---> Processed Frames ---> Visualizations
      |                 |                    |                   |
      |                 v                    v                   v
   Exporter <---- Data Processor <---- Extractor (Sample/Live)  Charts
```
Core layers are isolated (extraction, processing, analytics, visualization, export) for testability and substitution.

## 4. Data Model & Flow
1. Extraction: sample synthetic or (future) live Selenium scraping
2. Cleaning: coercion of dtypes, dedupe, sanitization, negative guard
3. Aggregation: daily to monthly rollups, market share derivation
4. Analytics: growth deltas, rolling volatility, drawdown, CV
5. Presentation: interactive charts & tables
6. Export: user-selected scope to CSV/XLSX/PDF

## 5. Tech Stack
| Layer | Tools |
|-------|-------|
| UI | Streamlit, CSS theme overrides |
| Data | Pandas, NumPy |
| Viz | Plotly |
| Export | Pandas (CSV/XLSX), FPDF/basic PDF module |
| Testing | Pytest |
| Optional Live | Selenium (planned) |

## 6. Quick Start
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/dashboard/main.py --server.port 8501
```
Open: http://localhost:8501

## 7. Run Modes
| Mode | Variable | Behavior |
|------|----------|----------|
| Sample (default) | USE_LIVE_VAHAN=0 | Synthetic randomized demo dataset |
| Live (planned) | USE_LIVE_VAHAN=1 | Real extraction via Selenium selectors |

## 8. Configuration & Environment
Create .env (optional):
```
USE_LIVE_VAHAN=0
DATA_EXPORT_DIR=data/exports
```
Ensure directory exists for exports. Defaults applied if unset.

## 9. Usage Guide
1. Select date range (daily granularity, monthly aggregation available)
2. Choose vehicle categories and dimensions (state/manufacturer)
3. Toggle metrics tabs (Growth, Volatility, Market Share, Raw)
4. Switch theme if desired
5. Export current filtered dataset

## 10. Analytics Implemented
| Metric | Description |
|--------|-------------|
| YoY Growth | (Current period vs same period previous year) |
| QoQ Growth | Sequential quarter delta |
| MoM Growth | Sequential month delta (if exposed) |
| Rolling Volatility | 30-day std of registrations |
| Coefficient of Variation | Rolling std / rolling mean (30d) |
| Max Drawdown | Peak-to-trough over rolling 30d window |
| Market Share | Entity share within date-category universe |

## 11. Exports
| Format | Method |
|--------|--------|
| CSV | Pandas to_csv |
| XLSX | Pandas ExcelWriter |
| PDF | Lightweight programmatic summary |

## 12. Theming
Custom CSS applied to Streamlit widgets for consistent contrast across light and dark modes (select boxes, buttons, calendars, popovers). Toggle available in header.

## 13. Testing & Quality
Run tests:
```bash
pytest -q
```
Coverage centers on data processing, growth/volatility calculations, and sample extraction workflow.

## 14. Performance Notes
- Vectorized Pandas operations
- Avoids expensive recomputation by isolating transformations
- Suitable for tens of thousands of rows in-memory; future caching layer planned

## 15. Security & Privacy
No PII handled. Sample mode only. Live scraping mode (planned) should respect target site terms and implement throttling & caching.

## 16. Roadmap
- Live Selenium integration & schema validation
- Streamlit + disk caching (parquet)
- Advanced analytics: anomaly flags, seasonality decomposition, forecasting
- Persistence (SQLite/Postgres) with incremental loads
- Extended PDF reporting (styled executive brief)
- Authentication & role-based access
- Alerting (email / webhook)
- NLP insight layer (natural language queries)

## 17. Contributing
Fork, branch, implement, add tests, ensure all pass, open PR. Adhere to modular separation and avoid embedding logic in the UI layer. Keep added dependencies minimal and documented.

## 18. FAQ
| Question | Answer |
|----------|--------|
| Why NaNs in early rows? | Prior-period data missing for growth/rolling windows |
| Can I plug real data now? | Set USE_LIVE_VAHAN=1 after implementing selectors |
| How to add a new metric? | Implement in analytics module; expose via UI tab |

## 19. Support
Open an issue or contact maintainer. Feature requests welcome.

## 20. License
MIT License. See LICENSE.

## Media (Optional)
Add demo video link: TBD (place link here)
Add screenshots in docs/images (dashboard_preview.png etc.)
