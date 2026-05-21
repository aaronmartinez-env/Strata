"""
complexity.py
-------------
Atmospheric Complexity Index (ACI).

Uses Shannon entropy over the four source attribution percentages.
High ACI = mixed, ambiguous atmospheric state (hard to attribute).
Low ACI  = one dominant source (clear attribution).

Max entropy with 4 equal sources = ln(4) ≈ 1.386
"""

import numpy as np
import pandas as pd


def compute_aci(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Shannon entropy across attribution scores as ACI.

    Required columns: saharan_pct, urban_pct, marine_pct, stagnation_pct

    Returns df with added column: ACI (float, range 0 to ln(4) ≈ 1.386)
    """
    df = df.copy()

    sources = df[["saharan_pct", "urban_pct", "marine_pct", "stagnation_pct"]].values

    # Add small epsilon to avoid log(0), then compute entropy row-wise
    sources = sources + 1e-12
    df["ACI"] = -np.sum(sources * np.log(sources), axis=1)

    # Normalise to [0, 1] for interpretability
    df["ACI_normalized"] = df["ACI"] / np.log(4)

    return df
