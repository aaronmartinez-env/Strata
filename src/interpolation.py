"""
interpolation.py
----------------
Spatial interpolation of pollution fields using scipy griddata.
Produces a continuous pollution surface from discrete station readings.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from scipy.interpolate import griddata
import os
from config import OUTPUT_PATH


def interpolate_field(
    df: pd.DataFrame,
    pollutant: str = "pm10",
    method: str = "cubic",
    resolution: int = 100,
    save: bool = True,
) -> np.ndarray:
    """
    Interpolate a pollution field over Valencia's spatial extent.

    Parameters
    ----------
    df        : DataFrame with latitude, longitude, and pollutant column
    pollutant : Which column to interpolate
    method    : griddata method: 'cubic', 'linear', or 'nearest'
    resolution: Grid resolution (higher = smoother, slower)
    save      : Whether to save the figure

    Returns np.ndarray of the interpolated grid.
    """
    # Use mean per station to avoid time-axis noise
    station_df = df.groupby("station").agg(
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        value=(pollutant, "mean"),
    ).reset_index()

    points = station_df[["longitude", "latitude"]].values
    values = station_df["value"].values

    lon_min, lon_max = points[:, 0].min(), points[:, 0].max()
    lat_min, lat_max = points[:, 1].min(), points[:, 1].max()

    # Add small padding so the grid isn't clipped at station edges
    pad_lon = (lon_max - lon_min) * 0.1
    pad_lat = (lat_max - lat_min) * 0.1

    grid_x, grid_y = np.mgrid[
        lon_min - pad_lon : lon_max + pad_lon : complex(resolution),
        lat_min - pad_lat : lat_max + pad_lat : complex(resolution),
    ]

    grid_z = griddata(points, values, (grid_x, grid_y), method=method)

    # Fallback: fill NaN edges with nearest-neighbour
    if np.isnan(grid_z).any():
        grid_z_nn = griddata(points, values, (grid_x, grid_y), method="nearest")
        grid_z = np.where(np.isnan(grid_z), grid_z_nn, grid_z)

    fig, ax = plt.subplots(figsize=(9, 7))

    norm = mcolors.PowerNorm(gamma=0.6, vmin=values.min(), vmax=values.max())
    im = ax.imshow(
        grid_z.T,
        extent=(lon_min - pad_lon, lon_max + pad_lon,
                lat_min - pad_lat, lat_max + pad_lat),
        origin="lower",
        cmap="YlOrRd",
        norm=norm,
        alpha=0.85,
    )

    ax.scatter(
        station_df["longitude"],
        station_df["latitude"],
        c="black",
        s=30,
        zorder=5,
        label="Stations",
    )

    for _, row in station_df.iterrows():
        ax.annotate(
            row["station"],
            xy=(row["longitude"], row["latitude"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color="black",
        )

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(f"{pollutant.upper()} (µg/m³)")

    ax.set_title(f"Interpolated {pollutant.upper()} Field – Valencia")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(fontsize=8)
    plt.tight_layout()

    if save:
        out_path = os.path.join(OUTPUT_PATH, "figures", f"interpolated_{pollutant}.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=150)
        print(f"  Figure saved to {out_path}")

    try:
        plt.show()
    except Exception:
        pass
    return grid_z
