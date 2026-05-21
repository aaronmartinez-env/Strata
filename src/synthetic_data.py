"""
synthetic_data.py
-----------------
Generates realistic Valencia-like air quality and meteorological data
for end-to-end pipeline testing before real data is connected.

Realistic ranges based on Mediterranean urban context:
  PM10:  20–120 µg/m³ (spikes to 200+ during calima)
  PM2.5: 8–45 µg/m³
  NO2:   15–90 µg/m³
  O3:    30–120 µg/m³
  Wind:  0–9 m/s (tramontane gusts excluded)
"""

import numpy as np
import pandas as pd
from config import VALENCIA_BOUNDS


# Real-ish Valencia monitoring station locations
STATIONS = [
    {"station": "Pista de Silla",      "latitude": 39.430, "longitude": -0.408},
    {"station": "Molí del Sol",         "latitude": 39.445, "longitude": -0.380},
    {"station": "Conselleria Meteo",    "latitude": 39.470, "longitude": -0.370},
    {"station": "Avda. Francia",        "latitude": 39.463, "longitude": -0.345},
    {"station": "Politècnic",           "latitude": 39.480, "longitude": -0.346},
    {"station": "Viveros",              "latitude": 39.479, "longitude": -0.364},
    {"station": "Cabanyal",             "latitude": 39.469, "longitude": -0.330},
    {"station": "Bulevard Sud",         "latitude": 39.450, "longitude": -0.393},
]


def _calima_signal(n, rng, intensity=1.0):
    """Returns a time-series bump representing a calima intrusion event."""
    signal = np.zeros(n)
    start = rng.integers(n // 4, 3 * n // 4)
    duration = rng.integers(12, 48)  # hours
    end = min(n, start + duration)
    envelope = np.hanning(end - start)
    signal[start:end] = envelope * intensity
    return signal, start, end


def generate_synthetic_data(
    n_hours: int = 720,          # 30 days
    n_calima_events: int = 2,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate a synthetic air quality + weather DataFrame.

    Parameters
    ----------
    n_hours         : Number of hourly timesteps.
    n_calima_events : How many Saharan dust intrusions to inject.
    seed            : Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame with one row per (station × hour).
    """
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-03-01", periods=n_hours, freq="h")
    records = []

    for station_info in STATIONS:

        # --- Base pollutant time series (diurnal + noise) ---
        hour_of_day = np.array([t.hour for t in timestamps])
        diurnal = np.sin(np.pi * hour_of_day / 12) * 0.4 + 0.6  # peaks midday

        pm10_base  = rng.uniform(25, 55, n_hours) * diurnal
        pm25_base  = pm10_base * rng.uniform(0.35, 0.55, n_hours)
        no2_base   = rng.uniform(20, 70, n_hours) * diurnal
        o3_base    = rng.uniform(35, 100, n_hours) * (1 - diurnal * 0.3)

        # --- Calima events ---
        calima_mask = np.zeros(n_hours, dtype=bool)
        for _ in range(n_calima_events):
            signal, start, end = _calima_signal(
                n_hours, rng, intensity=rng.uniform(120, 180)
            )
            pm10_base  += signal
            pm25_base  += signal * rng.uniform(0.1, 0.2)  # calima = coarse dominant
            calima_mask[start:end] = True

        # --- Wind ---
        wind_speed     = rng.uniform(0.5, 8.5, n_hours)
        wind_direction = rng.uniform(0, 360, n_hours)

        # During calima: southerly to southeasterly winds (150–220°)
        if calima_mask.any():
            wind_direction[calima_mask] = rng.uniform(150, 220, calima_mask.sum())
            wind_speed[calima_mask]     = rng.uniform(3, 7, calima_mask.sum())

        # --- Temperature & humidity (Mediterranean March–April range) ---
        temperature = 15 + 6 * np.sin(np.pi * hour_of_day / 12) + rng.normal(0, 1.5, n_hours)
        humidity    = 60 + rng.normal(0, 8, n_hours)
        humidity    = np.clip(humidity, 30, 95)

        # --- Clip to realistic ranges ---
        pm10_base  = np.clip(pm10_base,  5, 250)
        pm25_base  = np.clip(pm25_base,  2, 80)
        no2_base   = np.clip(no2_base,   5, 150)
        o3_base    = np.clip(o3_base,   10, 180)

        for i, ts in enumerate(timestamps):
            records.append({
                "datetime":       ts,
                **station_info,
                "pm25":           round(pm25_base[i], 2),
                "pm10":           round(pm10_base[i], 2),
                "no2":            round(no2_base[i], 2),
                "o3":             round(o3_base[i], 2),
                "wind_speed":     round(wind_speed[i], 2),
                "wind_direction": round(wind_direction[i], 1),
                "temperature":    round(temperature[i], 1),
                "humidity":       round(humidity[i], 1),
            })

    df = pd.DataFrame(records)
    df = df.sort_values(["datetime", "station"]).reset_index(drop=True)
    return df


def save_synthetic_data(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)
    print(f"Saved {len(df):,} rows to {path}")


if __name__ == "__main__":
    from config import BASE_PATH
    import os

    df = generate_synthetic_data()
    save_synthetic_data(df, os.path.join(BASE_PATH, "raw/air_quality.csv"))
    print(df.head())
    print(df.describe())
