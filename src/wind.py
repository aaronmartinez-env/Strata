"""
wind.py
-------
Wind vector field visualization.
Aggregates per station and plots directional vectors.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os
from config import OUTPUT_PATH


def plot_wind_vectors(df: pd.DataFrame, save: bool = True) -> None:
    """
    Plot mean wind vectors for each station.

    Parameters
    ----------
    df   : DataFrame with latitude, longitude, wind_speed, wind_direction
    save : Whether to save the figure to outputs/figures/
    """
    # Aggregate to one vector per station
    station_df = df.groupby("station").agg(
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        wind_speed=("wind_speed", "mean"),
        wind_direction=("wind_direction", "mean"),
    ).reset_index()

    direction_rad = np.radians(station_df["wind_direction"])
    u = station_df["wind_speed"] * np.sin(direction_rad)   # eastward component
    v = station_df["wind_speed"] * np.cos(direction_rad)   # northward component

    fig, ax = plt.subplots(figsize=(9, 7))

    q = ax.quiver(
        station_df["longitude"],
        station_df["latitude"],
        u, v,
        station_df["wind_speed"],
        cmap="viridis",
        scale=40,
        width=0.005,
    )

    plt.colorbar(q, ax=ax, label="Wind speed (m/s)")

    for _, row in station_df.iterrows():
        ax.annotate(
            row["station"],
            xy=(row["longitude"], row["latitude"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            color="dimgray",
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Mean Wind Field – Valencia Monitoring Stations")
    plt.tight_layout()

    if save:
        out_path = os.path.join(OUTPUT_PATH, "figures", "wind_vectors.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=150)
        print(f"  Figure saved to {out_path}")

    try:
        plt.show()
    except Exception:
        pass
