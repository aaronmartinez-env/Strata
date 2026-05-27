"""
spatial.py
----------
Interactive station map using folium.
Saves output to outputs/maps/.
"""

import folium
import pandas as pd
import os
from config import OUTPUT_PATH


def create_station_map(df: pd.DataFrame, save: bool = True) -> folium.Map:
    """
    Create an interactive folium map of monitoring stations.

    Each marker shows:
      - Station name
      - Mean PM10, PM2.5, scientific AQI (if available)
      - Colour-coded by mean AQI level

    Parameters
    ----------
    df   : DataFrame with latitude, longitude, station, pm10, pm25 columns
    save : Whether to save the HTML map to outputs/maps/

    Returns folium.Map object.
    """
    # Aggregate to one row per station for the map
    agg_cols = {
        "latitude":  "first",
        "longitude": "first",
        "pm10":      "mean",
        "pm25":      "mean",
    }
    if "aqi_scientific" in df.columns:
        agg_cols["aqi_scientific"] = "mean"
    if "calima_event" in df.columns:
        agg_cols["calima_event"] = "sum"

    station_df = df.groupby("station").agg(agg_cols).reset_index()

    # Drop stations with no coordinates before mapping
    station_df = station_df.dropna(subset=["latitude", "longitude"])

    if station_df.empty:
        raise ValueError("No stations with valid coordinates found. "
                         "Check STATION_COORDS in rvvcca_ingestion.py.")

    center_lat = station_df["latitude"].mean()
    center_lon = station_df["longitude"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for _, row in station_df.iterrows():
        aqi = row.get("aqi_scientific", 50)

        # Colour by AQI level
        if aqi < 33:
            color = "green"
        elif aqi < 66:
            color = "orange"
        else:
            color = "red"

        popup_lines = [
            f"<b>{row['station']}</b>",
            f"PM10 (mean): {row['pm10']:.1f} µg/m³",
            f"PM2.5 (mean): {row['pm25']:.1f} µg/m³",
        ]
        if "aqi_scientific" in row:
            popup_lines.append(f"AQI (scientific): {row['aqi_scientific']:.1f}")
        if "calima_event" in row:
            popup_lines.append(f"Calima hours: {int(row['calima_event'])}")

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=10,
            popup=folium.Popup("<br>".join(popup_lines), max_width=220),
            color=color,
            fill=True,
            fill_opacity=0.75,
        ).add_to(m)

    if save:
        out_path = os.path.join(OUTPUT_PATH, "maps", "station_map.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        m.save(out_path)
        print(f"  Map saved to {out_path}")

    return m
