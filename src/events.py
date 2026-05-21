"""
events.py
---------
Calima (Saharan dust intrusion) event detection.
Uses rolling statistics + PM10/PM2.5 ratio to flag episodes.
"""

import pandas as pd


def detect_calima_events(df: pd.DataFrame, window: int = 72) -> pd.DataFrame:
    """
    Detect Saharan dust (calima) intrusion events.

    Strategy:
      1. Rolling spike: PM10 exceeds a long-baseline rolling mean + 1.5 sigma
         (72-hour window captures gradual Saharan intrusions, not just
          instantaneous spikes -- calima events build over hours/days)
      2. Dust ratio: PM10/PM2.5 > 3 (coarse-dominant = mineral dust)
      3. Both must be true simultaneously

    Parameters
    ----------
    df     : DataFrame with pm10, pm25 columns
    window : Rolling baseline window in hours (default 72h = 3 days)

    Returns df with added columns:
      pm10_spike, dust_event, calima_event (bool), dust_ratio
    """
    df = df.copy()
    df = df.sort_values(["station", "datetime"]).reset_index(drop=True)

    df["dust_ratio"] = df["pm10"] / (df["pm25"] + 1e-6)

    # Rolling stats computed per station to avoid cross-station leakage
    grp = df.groupby("station")["pm10"]
    df["_pm10_roll_mean"] = grp.transform(
        lambda x: x.rolling(window=window, min_periods=6).mean()
    )
    df["_pm10_roll_std"] = grp.transform(
        lambda x: x.rolling(window=window, min_periods=6).std().fillna(0)
    )

    # 1.5-sigma threshold (not 2) -- calima is a sustained elevation, not a sharp spike
    df["pm10_spike"]   = df["pm10"] > (df["_pm10_roll_mean"] + 1.5 * df["_pm10_roll_std"])
    df["dust_event"]   = df["dust_ratio"] > 3
    df["calima_event"] = df["pm10_spike"] & df["dust_event"]

    df.drop(columns=["_pm10_roll_mean", "_pm10_roll_std"], inplace=True)

    n_events = df["calima_event"].sum()
    print(f"  Calima events detected: {n_events} observations "
          f"({n_events/len(df)*100:.1f}% of records)")

    return df
