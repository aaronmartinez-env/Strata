"""
attribution.py
--------------
Computes a probabilistic source attribution score for each observation,
breaking pollution into four components that sum to 1.0.

Fix vs original:
  - df.get() doesn't exist on DataFrames — replaced with proper column check
  - Row-by-row loop replaced with vectorised pandas operations
  - Division-by-zero guards preserved
"""

import numpy as np
import pandas as pd


def compute_attribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimate fractional source contributions for each observation.

    Required columns: pm10, pm25
    Optional columns: wind_speed

    Returns df with added columns:
      saharan_pct, urban_pct, marine_pct, stagnation_pct
      (each in [0, 1], all four sum to 1.0 per row)
    """
    df = df.copy()

    pm10 = df["pm10"]
    pm25 = df["pm25"]

    # --- Fix: proper column check instead of df.get() ---
    if "wind_speed" in df.columns:
        wind = df["wind_speed"]
    else:
        wind = pd.Series(np.zeros(len(df)), index=df.index)

    dust_ratio = pm10 / (pm25 + 1e-6)

    pm10_max  = pm10.max()
    pm25_max  = pm25.max()
    wind_max  = wind.max()

    # --- Vectorised scoring ---
    dust_score = (
        (dust_ratio / 5).clip(upper=1.0) *
        (pm10 / pm10_max)
    )

    urban_score = (
        (pm25 / pm25_max).clip(upper=1.0) *
        (1 - wind / (wind_max + 1e-6))
    )

    marine_score = (
        (1 - pm10 / pm10_max) *
        (wind / (wind_max + 1e-6))
    )

    stagnation_score = (
        (1 - wind / (wind_max + 1e-6)) *
        (pm10 / pm10_max)
    )

    total = dust_score + urban_score + marine_score + stagnation_score + 1e-6

    df["saharan_pct"]   = dust_score       / total
    df["urban_pct"]     = urban_score      / total
    df["marine_pct"]    = marine_score     / total
    df["stagnation_pct"]= stagnation_score / total

    return df
