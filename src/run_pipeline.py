"""
run_pipeline.py
---------------
AERIS end-to-end pipeline.

Run from the project root:
    python src/run_pipeline.py                  # auto-selects real or synthetic data
    python src/run_pipeline.py --fetch          # fetch fresh real data then run
    python src/run_pipeline.py --synthetic      # force synthetic data
    python src/run_pipeline.py --from 2022-01-01 --to 2022-06-30  # custom date range

Steps:
  1. Load or fetch data (real RVVCCA or synthetic fallback)
  2. Preprocess
  3. Compute scientific + public AQI
  4. Detect calima events
  5. Classify air masses
  6. Source attribution
  7. Atmospheric Complexity Index (ACI)
  8. Generate outputs (map, wind, interpolation, AQI comparison, report)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")

from config import BASE_PATH, OUTPUT_PATH
from data_loader import load_air_quality
from preprocessing import standardize_datetime, remove_missing, standardize_columns
from aqi_model import compute_scientific_aqi, compute_public_aqi, compute_aqi_divergence
from events import detect_calima_events
from air_mass import classify_air_mass
from attribution import compute_attribution
from complexity import compute_aci
from spatial import create_station_map
from wind import plot_wind_vectors
from interpolation import interpolate_field
from reporting import generate_report, plot_aqi_comparison
from analysis import run_analysis, save_findings, print_research_summary
from inject_findings import inject as inject_portfolio


def run(use_synthetic: bool = False, fetch_fresh: bool = False,
        date_from: str = "2022-01-01", date_to: str = "2022-03-31"):

    print("\n── AERIS Pipeline ──────────────────────────────────")

    # ── 1. Data loading ──────────────────────────────────────────────────────
    print("\n[1/8] Loading data...")

    if use_synthetic:
        # Force synthetic — generate it fresh
        from synthetic_data import generate_synthetic_data, save_synthetic_data
        print("  Generating synthetic Valencia data...")
        df = generate_synthetic_data(n_hours=720, n_calima_events=2, seed=42)
        raw_path = os.path.join(BASE_PATH, "raw", "air_quality.csv")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        save_synthetic_data(df, raw_path)

    elif fetch_fresh:
        # Fetch real data from RVVCCA API, overwriting cache
        from rvvcca_ingestion import load_or_fetch, data_quality_report
        print(f"  Fetching real RVVCCA data ({date_from} → {date_to})...")
        df = load_or_fetch(
            date_from=date_from,
            date_to=date_to,
            force_fetch=True,
        )
        if df.empty:
            print("  WARNING: Real data fetch returned empty. Falling back to synthetic.")
            from synthetic_data import generate_synthetic_data, save_synthetic_data
            df = generate_synthetic_data(n_hours=720, n_calima_events=2, seed=42)
            save_synthetic_data(df, os.path.join(BASE_PATH, "raw", "air_quality.csv"))
        else:
            data_quality_report(df)

    else:
        # Auto-select: real data if cached, else synthetic
        try:
            df = load_air_quality(prefer_real=True)
        except FileNotFoundError:
            print("  No data found — generating synthetic data...")
            from synthetic_data import generate_synthetic_data, save_synthetic_data
            df = generate_synthetic_data(n_hours=720, n_calima_events=2, seed=42)
            save_synthetic_data(df, os.path.join(BASE_PATH, "raw", "air_quality.csv"))

    print(f"  Shape after load: {df.shape}")

    # ── 2. Preprocess ────────────────────────────────────────────────────────
    print("\n[2/8] Preprocessing...")
    df = standardize_columns(df)
    df = standardize_datetime(df)
    before = len(df)
    df = remove_missing(df)
    print(f"  Rows: {before:,} → {len(df):,} after dropping nulls")

    # Guard: need at least these columns to proceed
    required = {"pm25", "pm10", "no2", "o3"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns after load: {missing_cols}\n"
                         f"Check column mapping in rvvcca_ingestion.py → _parse_records()")

    # ── 3. AQI ──────────────────────────────────────────────────────────────
    print("\n[3/8] Computing AQI...")
    df = compute_scientific_aqi(df)
    df = compute_public_aqi(df)
    df = compute_aqi_divergence(df)
    print(f"  Scientific AQI : {df['aqi_scientific'].min():.1f} – {df['aqi_scientific'].max():.1f}")
    print(f"  Public AQI     : {df['aqi_public'].min():.1f} – {df['aqi_public'].max():.1f}")
    print(f"  Mean divergence: {df['aqi_divergence'].mean():.2f}")

    # ── 4. Calima detection ──────────────────────────────────────────────────
    print("\n[4/8] Detecting calima events...")
    df = detect_calima_events(df)

    # ── 5. Air mass classification ───────────────────────────────────────────
    print("\n[5/8] Classifying air masses...")
    df = classify_air_mass(df)
    dist = df["air_mass_type"].value_counts()
    for mass, count in dist.items():
        print(f"  {mass:<20}: {count:>6} obs ({count/len(df)*100:.1f}%)")

    # ── 6. Attribution ───────────────────────────────────────────────────────
    print("\n[6/8] Computing source attribution...")
    df = compute_attribution(df)
    for src in ["saharan_pct", "urban_pct", "marine_pct", "stagnation_pct"]:
        print(f"  {src:<20}: mean={df[src].mean():.3f}")

    # ── 7. ACI ───────────────────────────────────────────────────────────────
    print("\n[7/8] Computing Atmospheric Complexity Index...")
    df = compute_aci(df)
    print(f"  Mean ACI (normalised): {df['ACI_normalized'].mean():.3f}")

    # ── 8. Outputs ───────────────────────────────────────────────────────────
    print("\n[8/9] Generating outputs...")

    create_station_map(df, save=True)
    plot_wind_vectors(df, save=True)
    interpolate_field(df, pollutant="pm10", save=True)
    plot_aqi_comparison(df, save=True)
    report = generate_report(df, save=True)

    # Save processed data
    processed_path = os.path.join(BASE_PATH, "processed", "aeris_processed.csv")
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    df.to_csv(processed_path, index=False)
    print(f"  Processed data → {processed_path}")

    # ── 9. Deep analysis ────────────────────────────────────────────────────
    print("\n[9/9] Running deep divergence analysis...")
    findings = run_analysis(df, verbose=False)
    save_findings(findings)
    print_research_summary(findings)

    # Auto-inject into portfolio HTML if it exists
    portfolio_path = os.path.join(
        os.path.dirname(__file__), "..", "aeris_portfolio.html"
    )
    inject_portfolio(portfolio_path, findings, verbose=True)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n── Pipeline Report ─────────────────────────────────")
    for k, v in report.items():
        print(f"  {k}: {v}")

    print("\n✓ AERIS pipeline complete.\n")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the AERIS pipeline")
    parser.add_argument("--synthetic", action="store_true",
                        help="Force synthetic data (skip real data)")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch fresh real data from RVVCCA API")
    parser.add_argument("--from", dest="date_from", default="2022-01-01",
                        help="Fetch start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", default="2022-03-31",
                        help="Fetch end date (YYYY-MM-DD)")
    args = parser.parse_args()

    run(
        use_synthetic=args.synthetic,
        fetch_fresh=args.fetch,
        date_from=args.date_from,
        date_to=args.date_to,
    )
