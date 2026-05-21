"""
aqi_model.py
------------
Scientific AQI model + simplified public AQI simulation.

The scientific AQI is a weighted composite of normalized pollutants.
The public AQI mimics simplified consumer representations (e.g. weather apps)
that often rely only on PM10 or a basic index, losing nuance.

This contrast is the core of AERIS's research question.
"""

import pandas as pd
import numpy as np
from config import WEIGHTS


def normalize(series: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 100]."""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - min_val) / (max_val - min_val)) * 100


def compute_scientific_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted composite AQI from all four pollutants.
    Output column: aqi_scientific (0–100)
    Handles sparse columns: pollutants with all-NaN are skipped and
    weights are redistributed among available pollutants.
    """
    df = df.copy()

    available = {}
    for p in ["pm25", "pm10", "no2", "o3"]:
        if p in df.columns and df[p].notna().any():
            df[f"{p}_n"] = normalize(df[p])
            available[p] = WEIGHTS[p]
        else:
            df[f"{p}_n"] = 0.0

    # Redistribute weights if some pollutants are missing
    total_weight = sum(available.values()) if available else 1.0

    df["aqi_scientific"] = sum(
        (w / total_weight) * df[f"{p}_n"]
        for p, w in available.items()
    ) if available else float("nan")

    return df


def compute_public_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simplified public-facing AQI — PM10 only, coarsely binned.
    Simulates what weather apps and public dashboards typically show.

    Bins (WHO-inspired, simplified):
      0–25  → Good
      25–50 → Moderate
      50–75 → Unhealthy for sensitive groups
      75+   → Unhealthy
    """
    df = df.copy()

    df["aqi_public"] = normalize(df["pm10"])

    bins   = [0, 25, 50, 75, 100]
    labels = ["Good", "Moderate", "Sensitive", "Unhealthy"]
    df["aqi_public_label"] = pd.cut(
        df["aqi_public"], bins=bins, labels=labels, include_lowest=True
    )

    return df


def compute_aqi_divergence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Divergence between scientific and public AQI.
    High divergence = public representation is misleading.
    """
    df = df.copy()
    df["aqi_divergence"] = (df["aqi_scientific"] - df["aqi_public"]).abs()
    return df
