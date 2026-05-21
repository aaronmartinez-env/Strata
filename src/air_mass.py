"""
air_mass.py
-----------
Classifies each observation into one of four air-mass regimes
using rule-based atmospheric logic.

Fix vs original:
  - np.percentile computed ONCE before the loop (not inside it)
  - Conditions are mutually exclusive and clearly ordered
  - Works on any DataFrame with the required columns
"""

import numpy as np
import pandas as pd


AIR_MASS_TYPES = [
    "saharan_dust",
    "urban_pollution",
    "marine_air",
    "stagnant_mix",
]


def classify_air_mass(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each row into an air-mass type.

    Required columns: pm10, pm25, wind_speed (optional but recommended)

    Returns df with added columns:
      dust_ratio     : pm10 / pm25 ratio
      air_mass_type  : one of AIR_MASS_TYPES
    """
    df = df.copy()

    df["dust_ratio"] = df["pm10"] / (df["pm25"] + 1e-6)

    # Precompute thresholds once — this was the original bug
    pm10_p75 = df["pm10"].quantile(0.75)
    pm10_p40 = df["pm10"].quantile(0.40)

    wind = df["wind_speed"] if "wind_speed" in df.columns else pd.Series(
        np.zeros(len(df)), index=df.index
    )

    # Vectorised classification (no row loop needed)
    conditions = [
        # 1. Saharan dust: coarse-dominant, high PM10
        (df["dust_ratio"] > 3) & (df["pm10"] > pm10_p75),

        # 2. Urban pollution: fine-dominant, low wind
        (df["pm25"] > df["pm10"] * 0.6) & (wind < 3),

        # 3. Marine air: low PM10, reasonable wind
        (df["pm10"] < pm10_p40) & (wind >= 4),
    ]
    choices = ["saharan_dust", "urban_pollution", "marine_air"]

    df["air_mass_type"] = np.select(conditions, choices, default="stagnant_mix")

    return df
