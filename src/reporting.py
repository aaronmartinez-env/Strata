"""
reporting.py
------------
Summary and reporting layer for AERIS.
Answers the core research question: how well do public AQI
representations reflect actual atmospheric conditions?
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from config import OUTPUT_PATH


# ── Per-row narrative ────────────────────────────────────────────────────────

def generate_summary(row: pd.Series) -> str:
    """Return a plain-language summary for a single observation."""

    air_mass = row.get("air_mass_type", "unknown")
    calima   = row.get("calima_event", False)
    aci      = row.get("ACI_normalized", None)

    if calima:
        base = "Active Saharan dust intrusion (calima). Coarse particle concentrations elevated."
    elif air_mass == "saharan_dust":
        base = "Likely Saharan dust influence with elevated coarse particle concentrations."
    elif air_mass == "urban_pollution":
        base = "Urban pollution accumulation driven by low wind dispersion."
    elif air_mass == "marine_air":
        base = "Marine airflow associated with lower pollutant accumulation."
    else:
        base = "Mixed stagnant atmospheric conditions."

    if aci is not None:
        if aci > 0.8:
            base += " Atmospheric state is highly mixed (high ACI) — source attribution is uncertain."
        elif aci < 0.3:
            base += " Dominant single source — clear attribution (low ACI)."

    return base


# ── Aggregate report ─────────────────────────────────────────────────────────

def generate_report(df: pd.DataFrame, save: bool = True) -> dict:
    """
    Generate a summary report answering AERIS's research question.

    Returns a dict of key findings. Optionally saves a text report
    and a divergence plot.
    """
    report = {}

    # --- Air mass distribution ---
    if "air_mass_type" in df.columns:
        dist = df["air_mass_type"].value_counts(normalize=True) * 100
        report["air_mass_distribution_%"] = dist.round(1).to_dict()

    # --- Calima summary ---
    if "calima_event" in df.columns:
        calima_hours = df["calima_event"].sum()
        total_hours  = len(df)
        report["calima_event_hours"]   = int(calima_hours)
        report["calima_event_pct"]     = round(calima_hours / total_hours * 100, 2)

    # --- AQI divergence (core research question) ---
    if "aqi_divergence" in df.columns:
        report["mean_aqi_divergence"]   = round(df["aqi_divergence"].mean(), 2)
        report["max_aqi_divergence"]    = round(df["aqi_divergence"].max(), 2)
        report["pct_high_divergence"]   = round(
            (df["aqi_divergence"] > 20).sum() / len(df) * 100, 2
        )

        # Divergence during calima vs normal
        if "calima_event" in df.columns:
            calima_div = df.loc[df["calima_event"], "aqi_divergence"].mean()
            normal_div = df.loc[~df["calima_event"], "aqi_divergence"].mean()
            report["mean_divergence_during_calima"] = round(calima_div, 2)
            report["mean_divergence_normal"]        = round(normal_div, 2)

    # --- ACI summary ---
    if "ACI_normalized" in df.columns:
        report["mean_aci"] = round(df["ACI_normalized"].mean(), 3)

    # --- Save text report ---
    if save:
        os.makedirs(os.path.join(OUTPUT_PATH, "reports"), exist_ok=True)
        report_path = os.path.join(OUTPUT_PATH, "reports", "aeris_report.txt")

        with open(report_path, "w") as f:
            f.write("AERIS — Summary Report\n")
            f.write("=" * 50 + "\n\n")
            for k, v in report.items():
                f.write(f"{k}:\n  {v}\n\n")

        print(f"  Report saved to {report_path}")

    return report


# ── Divergence plot ──────────────────────────────────────────────────────────

def plot_aqi_comparison(df: pd.DataFrame, save: bool = True) -> None:
    """
    Plot scientific vs public AQI over time for one station,
    highlighting calima events and divergence.
    """
    station = df["station"].iloc[0]
    sdf = df[df["station"] == station].sort_values("datetime")

    # Drop rows with NaT datetime — can't be plotted on a time axis
    sdf = sdf[sdf["datetime"].notna()].copy()
    if sdf.empty:
        print(f"  Skipping AQI comparison plot — no valid timestamps for {station}")
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax1.plot(sdf["datetime"], sdf["aqi_scientific"], label="Scientific AQI",
             color="#2c7bb6", linewidth=1.2)
    ax1.plot(sdf["datetime"], sdf["aqi_public"],    label="Public AQI (PM10 only)",
             color="#d7191c", linewidth=1.2, linestyle="--")

    if "calima_event" in sdf.columns:
        calima_times = sdf.loc[sdf["calima_event"] & sdf["datetime"].notna(), "datetime"]
        for dt in calima_times:
            ax1.axvline(dt, color="sandybrown", alpha=0.15, linewidth=0.8)

    ax1.set_ylabel("AQI Score (0–100)")
    ax1.set_title(f"Scientific vs Public AQI — {station}")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.fill_between(sdf["datetime"], sdf["aqi_divergence"],
                     color="#f4a582", alpha=0.7, label="AQI Divergence")
    ax2.set_ylabel("Divergence (absolute)")
    ax2.set_xlabel("Date")
    ax2.set_title("AQI Representation Gap (higher = public AQI is more misleading)")
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()

    if save:
        out_path = os.path.join(OUTPUT_PATH, "figures", "aqi_comparison.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=150)
        print(f"  Figure saved to {out_path}")

    try:
        plt.show()
    except Exception:
        pass
