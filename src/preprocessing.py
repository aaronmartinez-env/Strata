"""
preprocessing.py
"""
import pandas as pd


def standardize_datetime(df, column="datetime"):
    df[column] = pd.to_datetime(df[column])
    return df


def remove_missing(df):
    """
    Drop rows only where ALL core pollutant columns are null.
    Bonus columns (nh3, noise, pressure, etc.) are allowed to be sparse.
    """
    core = ["pm25", "pm10", "no2", "o3"]

    # Keep rows that have at least one core pollutant reading
    available_core = [c for c in core if c in df.columns]
    before = len(df)
    df = df.dropna(subset=available_core, how="all")
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows where all core pollutants are null.")
    print(f"  Kept {len(df):,} rows.")
    return df


def standardize_columns(df):
    df.columns = [c.lower().strip() for c in df.columns]
    return df
