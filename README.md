# AERIS — Atmospheric Interpretation System

**An exploratory atmospheric representation framework for Valencia, Spain**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey.svg)](https://opendata.vlci.valencia.es)
[![Pipeline: Python 3.12](https://img.shields.io/badge/Python-3.12-green.svg)](https://python.org)

🌐 **Live portfolio:** [aaronmartinez-env.github.io/AERIS/aeris_portfolio.html](https://aaronmartinez-env.github.io/AERIS/aeris_portfolio.html)

---

## Research question

> How accurately do public-facing AQI representations reflect actual atmospheric conditions in Valencia?

AERIS quantifies the divergence between simplified public air quality indices (typically PM10-only) and a custom multi-pollutant composite index (CMPI) incorporating PM2.5, PM10, NO₂, and O₃. All analysis is applied to 160,076 hourly observations from Valencia's RVVCCA monitoring network across January 2021 – December 2022.

---

## Key findings

| Finding | Value | Source |
|---------|-------|--------|
| Mean CMPI divergence | 4.22 index pts | RVVCCA 2021–2022 |
| Max single-hour gap | 50.72 index pts | RVVCCA 2021–2022 |
| Peak divergence hour | 06:00 (NO₂ accumulation) | RVVCCA 2021–2022 |
| Min divergence hour | 17:00 (afternoon mixing) | RVVCCA 2021–2022 |
| NO₂ correlation with divergence | r = 0.38 | RVVCCA 2021–2022 |
| Calima hours detected | 2,591 (1.62% of obs.) | RVVCCA 2021–2022 |
| Public over-reads during calima | 35.8% of calima hours | RVVCCA 2021–2022 |
| Max hourly PM10 | 460 µg/m³ at Valencia Olivereta (2022-08-13) | RVVCCA 2021–2022 |
| Mean ACI | 0.743 | RVVCCA 2021–2022 |

All values are pipeline-derived. No values are manually hardcoded in the frontend.

---

## What AERIS is

AERIS is an **exploratory atmospheric interpretation framework** — not a replacement for official AQI systems. It:

- Builds a custom multi-pollutant composite index (CMPI) for comparative analysis
- Quantifies divergence between the CMPI and simplified public PM10-only indices
- Detects probable Saharan dust (calima) intrusion events using a dual-criterion heuristic
- Classifies atmospheric regimes (Saharan, urban, marine, stagnant) using rule-based logic
- Quantifies source attribution ambiguity via the Atmospheric Complexity Index (ACI)
- Visualises findings through an interactive atmospheric portfolio

AERIS does **not** validate health outcomes, certify toxicological risk, or replace official RVVCCA reporting.

---

## Data source

| Field | Value |
|-------|-------|
| Dataset | RVVCCA — Datos horarios calidad del aire, 2021–2022 |
| Publisher | Ajuntament de València / Open Data Valencia |
| URL | [opendata.vlci.valencia.es](https://opendata.vlci.valencia.es) |
| Licence | Creative Commons Attribution 4.0 (CC BY 4.0) |
| Coverage | January 2021 – December 2022 · 12 stations · Hourly |
| Raw rows | 201,480 × 30 columns |
| Valid rows | 160,076 (after quality filtering) |

The data is **not included in this repository**. Download it automatically by running:

```bash
python src/rvvcca_ingestion.py
```

---

## Project structure

```
AERIS/
├── src/
│   ├── run_pipeline.py        # Main entry point — runs all 9 steps
│   ├── rvvcca_ingestion.py    # Downloads and parses RVVCCA data
│   ├── data_loader.py         # Unified data loading (real or synthetic)
│   ├── preprocessing.py       # Datetime parsing, null handling
│   ├── aqi_model.py           # CMPI and public AQI computation
│   ├── events.py              # Calima (Saharan dust) detection
│   ├── air_mass.py            # Air mass classification
│   ├── attribution.py         # Source attribution scoring
│   ├── complexity.py          # Atmospheric Complexity Index (ACI)
│   ├── analysis.py            # Deep divergence analysis + findings export
│   ├── inject_findings.py     # Injects pipeline data into portfolio HTML
│   ├── spatial.py             # Interactive station map (folium)
│   ├── interpolation.py       # Spatial PM10 interpolation (scipy)
│   ├── wind.py                # Wind vector visualisation
│   ├── reporting.py           # Summary figures and reports
│   └── synthetic_data.py      # Synthetic data generator (dev/testing only)
├── data/
│   ├── raw/                   # Downloaded CSVs (git-ignored — see above)
│   ├── processed/             # Pipeline output CSVs (git-ignored)
│   └── spatial/               # Spatial reference files
├── outputs/
│   ├── figures/               # PNG charts
│   ├── maps/                  # Folium HTML maps
│   └── reports/               # aeris_findings.json · aeris_report.txt
├── notebooks/                 # Jupyter exploration notebooks
├── aeris_portfolio.html       # Interactive portfolio — open in any browser
├── requirements.txt
└── README.md
```

---

## Pipeline

AERIS runs as a single command:

```bash
python src/run_pipeline.py
```

This executes 9 sequential steps:

1. **Load data** — real RVVCCA data if cached, synthetic fallback for development
2. **Preprocess** — datetime parsing, null handling, column standardisation
3. **Compute CMPI** — weighted composite + public AQI + divergence
4. **Detect calima** — dual-criterion Saharan dust detection (PM10 spike + dust ratio)
5. **Classify air masses** — rule-based regime classification
6. **Source attribution** — probabilistic scoring across four source types
7. **Compute ACI** — Shannon entropy over attribution scores
8. **Generate outputs** — maps, charts, interpolated fields, reports
9. **Deep analysis + inject** — exports `aeris_findings.json` and updates `aeris_portfolio.html`

Additional flags:

```bash
python src/run_pipeline.py --fetch          # Re-download RVVCCA data
python src/run_pipeline.py --synthetic      # Force synthetic data (dev mode)
python src/rvvcca_ingestion.py --force      # Re-download and re-parse raw data
python src/inject_findings.py               # Update portfolio without re-running pipeline
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/aaronmartinez-env/AERIS.git
cd AERIS

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download the RVVCCA dataset
python src/rvvcca_ingestion.py

# Run the full pipeline
python src/run_pipeline.py
```

---

## Methodology notes

### Custom Multi-Pollutant Composite Index (CMPI)

The CMPI is a **research construct** — not a regulatory or medically validated index.

| Pollutant | Weight | Rationale |
|-----------|--------|-----------|
| PM2.5 | 40% | EU Directive 2008/50/EC and WHO 2021 relative emphasis |
| PM10 | 30% | Spanish regulatory monitoring emphasis |
| NO₂ | 20% | Urban combustion sources |
| O₃ | 10% | Secondary photochemical pollution |

All pollutants are min-max normalised to [0, 100] across the full dataset before weighting. CMPI values are dataset-relative and not directly comparable across different datasets or time periods.

### Calima detection

Saharan dust intrusion events are flagged using a dual per-station criterion:

```
Criterion 1: PM10 > (72-hour rolling station mean + 1.5σ)
Criterion 2: PM10 / PM2.5 ratio > 3.0
Both must be satisfied simultaneously
```

The ratio threshold is informed by Rodríguez et al. (2001) and Escudero et al. (2005). No back-trajectory analysis (HYSPLIT) was applied — the criterion is a heuristic proxy.

### Atmospheric Complexity Index (ACI)

Shannon entropy applied to four rule-based source attribution scores, normalised to [0, 1] by dividing by ln(4). The ACI is a relative indicator of within-dataset atmospheric ambiguity — not an established atmospheric science metric.

---

## References

- European Parliament (2008). Directive 2008/50/EC on ambient air quality. *Official Journal of the European Union.*
- World Health Organization (2021). *WHO Global Air Quality Guidelines.* Geneva: WHO.
- Rodríguez, S., et al. (2001). Saharan dust contributions to PM10 and TSP levels in Southern and Eastern Spain. *Atmospheric Environment, 35*(14), 2433–2447.
- Escudero, M., et al. (2005). A methodology for the quantification of the net African dust load in air quality monitoring networks. *Atmospheric Environment, 39*(26), 4796–4808.
- Millán, M.M., et al. (2000). Ozone cycles in the western Mediterranean basin. *Journal of Geophysical Research: Atmospheres, 105*(D6), 7209–7236.
- Shannon, C.E. (1948). A mathematical theory of communication. *Bell System Technical Journal, 27*(3), 379–423.
- European Environment Agency (2023). *Air Quality in Europe 2023.* Copenhagen: EEA.

---

## Reproducibility

Every scientific value displayed in `aeris_portfolio.html` is derived from the RVVCCA dataset through the pipeline. The data flow is strictly enforced:

```
data/raw/air_quality_real.csv
  → src/analysis.py
  → outputs/reports/aeris_findings.json
  → src/inject_findings.py
  → aeris_portfolio.html
```

No scientific values are manually hardcoded in the frontend. The data block in `aeris_portfolio.html` is stamped with a pipeline generation timestamp on every run.

---

## Licence

- **Code:** MIT License — see [LICENSE](LICENSE)
- **Data:** CC BY 4.0 — Ajuntament de València / Open Data Valencia
- **Portfolio:** free to view and share with attribution

---

*AERIS — Environmental Science Portfolio · Aaron Martinez · 2025*
