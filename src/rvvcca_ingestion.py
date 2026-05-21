"""
rvvcca_ingestion.py
--------------------
Downloads and processes real air quality data from the
Open Data Valencia portal (RVVCCA — Red Valenciana de Vigilancia
y Control de la Contaminacion Atmosferica).

Sources (confirmed working URLs as of May 2026):
  Hourly 2021-2022:
    https://opendata.vlci.valencia.es/dataset/rvvcca_d_horarios_2021-2022
  Daily 2004-2022 (fallback):
    https://opendata.vlci.valencia.es/dataset/rvvcca

No API key needed. Licence: CC BY 4.0.

Usage (from project root, venv active):
  python src/rvvcca_ingestion.py                        # download & cache
  python src/rvvcca_ingestion.py --from 2021-03-01 --to 2021-06-30
  python src/rvvcca_ingestion.py --force                # re-download even if cached
  python src/rvvcca_ingestion.py --daily                # use daily dataset instead
"""

import requests
import pandas as pd
import os
import sys
import argparse
from io import StringIO

sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_PATH

# ── Confirmed download URLs ───────────────────────────────────────────────────

HOURLY_CSV_URL = (
    "https://opendata.vlci.valencia.es/dataset/"
    "6b0b7ec3-0aff-4757-bf1c-0a95cda7e98d/resource/"
    "19b5a1a7-5888-4d3e-b69b-3c1436d64e6e/download/"
    "rvvcca_d_horarios_2021-2022.csv"
)

# Daily dataset — longer history (2004-2022), one row per day per station
# Useful if hourly is unavailable or you want multi-year trend analysis
DAILY_CSV_URL = (
    "https://opendata.vlci.valencia.es/dataset/"
    "rvvcca/resource/rvvcca/download/rvvcca.csv"
)

# ── Station coordinates ───────────────────────────────────────────────────────

STATION_COORDS = {
    "Avda. Francia":       {"latitude": 39.4632, "longitude": -0.3451},
    "Av. Francia":         {"latitude": 39.4632, "longitude": -0.3451},
    "Bulevar Sur":         {"latitude": 39.4501, "longitude": -0.3928},
    "Bulevard Sud":        {"latitude": 39.4501, "longitude": -0.3928},
    "Molino del Sol":      {"latitude": 39.4447, "longitude": -0.3802},
    "Moli del Sol":        {"latitude": 39.4447, "longitude": -0.3802},
    "Pista Silla":         {"latitude": 39.4298, "longitude": -0.4083},
    "Pista de Silla":      {"latitude": 39.4298, "longitude": -0.4083},
    "Politecnico":         {"latitude": 39.4800, "longitude": -0.3463},
    "Politecnic":          {"latitude": 39.4800, "longitude": -0.3463},
    "Politècnic":          {"latitude": 39.4800, "longitude": -0.3463},
    "U. Politecnica":      {"latitude": 39.4800, "longitude": -0.3463},
    "Viveros":             {"latitude": 39.4793, "longitude": -0.3640},
    "Vivers":              {"latitude": 39.4793, "longitude": -0.3640},
    "Centro":              {"latitude": 39.4698, "longitude": -0.3763},
    "Centre":              {"latitude": 39.4698, "longitude": -0.3763},
    "Conselleria Meteo":   {"latitude": 39.4700, "longitude": -0.3700},
    "Conselleria":         {"latitude": 39.4700, "longitude": -0.3700},
    "Nazaret Meteo":       {"latitude": 39.4540, "longitude": -0.3370},
    "Natzaret Meteo":      {"latitude": 39.4540, "longitude": -0.3370},
    "Puerto Valencia":     {"latitude": 39.4562, "longitude": -0.3220},
    "Puerto València":     {"latitude": 39.4562, "longitude": -0.3220},
    "Port Valencia":       {"latitude": 39.4562, "longitude": -0.3220},
    "Port València":       {"latitude": 39.4562, "longitude": -0.3220},
    # Stations confirmed in 2021-2022 download
    "Valencia Centro":              {"latitude": 39.4698, "longitude": -0.3763},
    "Valencia Olivereta":           {"latitude": 39.4680, "longitude": -0.4050},
    "Puerto llit antic Turia":      {"latitude": 39.4590, "longitude": -0.3280},
    "Puerto Moll Trans. Ponent":    {"latitude": 39.4510, "longitude": -0.3190},
}

# ── Column mapping (raw CSV -> AERIS standard) ────────────────────────────────

COLUMN_MAP = {
    # Station & time
    "estacion":                 "station",
    "estacio":                  "station",
    "fecha":                    "fecha_raw",
    "hora":                     "hora_raw",
    # Particulates
    "pm1":                      "pm1",
    "pm2_5":                    "pm25",
    "pm2.5":                    "pm25",
    "pm10":                     "pm10",
    # Gases
    "no":                       "no",
    "no2":                      "no2",
    "nox":                      "nox",
    "o3":                       "o3",
    "so2":                      "so2",
    "co":                       "co",
    "nh3":                      "nh3",
    # Meteorology
    "velocidad_del_viento":     "wind_speed",
    "velocitat_del_vent":       "wind_speed",
    "velocidad_viento":         "wind_speed",
    "velocidad del viento":     "wind_speed",
    "direccion_del_viento":     "wind_direction",
    "direccio_del_vent":        "wind_direction",
    "direccion_viento":         "wind_direction",
    "direccion del viento":     "wind_direction",
    "temperatura":              "temperature",
    "humedad_relativa":         "humidity",
    "humitat_relativa":         "humidity",
    "humedad relativa":         "humidity",
    "presion":                  "pressure",
    "pressio":                  "pressure",
    "precipitacion":            "precipitation",
    "precipitacio":             "precipitation",
    "radiacion":                "radiation",
    "radiacio":                 "radiation",
    "velocidad_maxima_viento":  "wind_speed_max",
    "velocidad maxima del viento": "wind_speed_max",
    "velocidad maxima viento":  "wind_speed_max",
    "ruido":                    "noise",
    "soroll":                   "noise",
}


# ── Download ──────────────────────────────────────────────────────────────────

def download_csv(url: str, verbose: bool = True) -> pd.DataFrame:
    """
    Download the RVVCCA CSV and return a raw DataFrame.
    Handles encoding detection and separator sniffing automatically.
    """
    if verbose:
        print(f"Downloading from:\n  {url}")
        print("  (this may take 20-60 seconds for the full file)...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            f"\nCould not connect to {url}\n"
            f"Error: {e}\n\n"
            f"Check that the URL is still valid by opening it in your browser."
        )
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(
            f"\nHTTP error downloading data: {e}\n"
            f"Try opening the URL in your browser to confirm it still works:\n  {url}"
        )

    # Detect encoding
    content = response.content
    for encoding in ["utf-8-sig", "utf-8", "latin-1", "iso-8859-1"]:
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("utf-8", errors="replace")

    # Sniff separator (Spanish open data often uses semicolons)
    first_line = text.split("\n")[0]
    sep = ";" if first_line.count(";") > first_line.count(",") else ","

    df = pd.read_csv(StringIO(text), sep=sep, low_memory=False)

    if verbose:
        print(f"  Downloaded: {len(df):,} rows x {len(df.columns)} columns")
        print(f"  Raw columns: {list(df.columns)}")

    return df


# ── Parse & normalise ─────────────────────────────────────────────────────────

def parse_and_normalise(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Normalise raw RVVCCA CSV into AERIS standard format.
    """
    # 1. Normalise column names
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    if verbose:
        print(f"\n  Columns after mapping: {list(df.columns)}")

    # 2. Build datetime
    if "fecha_raw" in df.columns and "hora_raw" in df.columns:
        hora_sample = str(df["hora_raw"].iloc[0])

        # Hora column can be either:
        #   "14:00:00" (full time string) — extract HH directly
        #   14         (integer 1-24)     — subtract 1 to get 0-based
        if ":" in hora_sample:
            # Full time string like "9:00:00" or "14:00:00"
            # Parse hour component properly — str[:5] breaks on single-digit hours
            hora_parsed = pd.to_datetime(
                df["hora_raw"].astype(str), format="%H:%M:%S", errors="coerce"
            )
            # Fallback for HH:MM format
            mask_nat = hora_parsed.isna()
            if mask_nat.any():
                hora_parsed[mask_nat] = pd.to_datetime(
                    df.loc[mask_nat, "hora_raw"].astype(str),
                    format="%H:%M", errors="coerce"
                )
            hora_str = hora_parsed.dt.hour.fillna(0).astype(int).astype(str).str.zfill(2) + ":00"
        else:
            # Integer 1-24 — convert to 0-based HH:MM
            hora_int = pd.to_numeric(df["hora_raw"], errors="coerce").fillna(1).astype(int)
            hora_0based = (hora_int - 1).clip(0, 23)
            hora_str = hora_0based.astype(str).str.zfill(2) + ":00"

        dt_str = df["fecha_raw"].astype(str) + " " + hora_str

        # Try ISO format first (YYYY-MM-DD HH:MM), then Spanish (DD/MM/YYYY HH:MM)
        df["datetime"] = pd.to_datetime(dt_str, format="%Y-%m-%d %H:%M", errors="coerce")

        mask = df["datetime"].isna()
        if mask.any():
            df.loc[mask, "datetime"] = pd.to_datetime(
                dt_str[mask], format="%d/%m/%Y %H:%M", errors="coerce"
            )
        # Final fallback
        mask = df["datetime"].isna()
        if mask.any():
            df.loc[mask, "datetime"] = pd.to_datetime(
                dt_str[mask], dayfirst=True, errors="coerce"
            )

        parsed_ok = df["datetime"].notna().sum()
        parsed_pct = parsed_ok / len(df) * 100
        print(f"  Datetime parsed: {parsed_ok:,}/{len(df):,} rows ({parsed_pct:.1f}%)")
        if parsed_pct < 95:
            print(f"  ⚠ Sample raw values: fecha={df['fecha_raw'].iloc[0]!r}, "
                  f"hora={df['hora_raw'].iloc[0]!r}")
            print(f"  ⚠ dt_str sample: {dt_str.iloc[0]!r}")
    elif "fecha_raw" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["fecha_raw"], dayfirst=True, errors="coerce"
        )
    else:
        available = [c for c in df.columns if "fec" in c or "dat" in c or "hora" in c]
        raise ValueError(
            f"Could not find a date column.\n"
            f"Possible date-like columns in file: {available}\n"
            f"Full column list: {list(df.columns)}\n"
            f"Add the correct mapping to COLUMN_MAP in rvvcca_ingestion.py"
        )

    # 3. Fix decimal separator and cast numerics
    numeric_cols = [
        "pm1", "pm25", "pm10", "no", "no2", "nox", "o3", "so2", "co", "nh3",
        "wind_speed", "wind_direction", "wind_speed_max",
        "temperature", "humidity", "pressure", "precipitation", "radiation", "noise",
    ]
    for col in numeric_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = (
                    df[col].astype(str)
                    .str.replace(",", ".", regex=False)
                    .str.strip()
                )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Add coordinates
    if "station" not in df.columns:
        available = [c for c in df.columns if "estac" in c or "station" in c]
        raise ValueError(
            f"No 'station' column found after mapping.\n"
            f"Possible station columns: {available}\n"
            f"Add the correct mapping to COLUMN_MAP."
        )

    df["latitude"]  = df["station"].map(lambda s: _lookup_coord(s, "latitude"))
    df["longitude"] = df["station"].map(lambda s: _lookup_coord(s, "longitude"))

    missing_coords = df[df["latitude"].isna()]["station"].unique()
    if len(missing_coords):
        print(f"  ⚠ No coordinates found for: {list(missing_coords)}")
        print(f"    Add them to STATION_COORDS in rvvcca_ingestion.py")

    # 5. Select AERIS standard columns (plus bonus pollutants if present)
    core = ["datetime", "station", "latitude", "longitude",
            "pm25", "pm10", "no2", "o3",
            "wind_speed", "wind_direction", "temperature", "humidity"]
    bonus = ["pm1", "no", "nox", "so2", "co", "nh3",
             "pressure", "precipitation", "radiation", "wind_speed_max", "noise"]

    keep = [c for c in core if c in df.columns] + \
           [c for c in bonus if c in df.columns]
    df = df[keep]
    df = df.sort_values(["station", "datetime"]).reset_index(drop=True)

    return df


def _lookup_coord(name: str, key: str):
    """Return lat or lon for a station name with fuzzy fallback."""
    if name in STATION_COORDS:
        return STATION_COORDS[name][key]
    name_lower = str(name).lower()
    for k, v in STATION_COORDS.items():
        if k.lower() in name_lower or name_lower in k.lower():
            return v[key]
    return None


# ── Date filter ───────────────────────────────────────────────────────────────

def filter_dates(df, date_from=None, date_to=None):
    if date_from:
        df = df[df["datetime"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["datetime"] <= pd.Timestamp(date_to) + pd.Timedelta(days=1)]
    return df.reset_index(drop=True)


# ── Quality report ────────────────────────────────────────────────────────────

def data_quality_report(df: pd.DataFrame) -> None:
    print("\n── Data Quality Report ─────────────────────────────")
    print(f"  Shape      : {df.shape}")
    print(f"  Date range : {df['datetime'].min()} → {df['datetime'].max()}")
    print(f"  Stations   : {sorted(df['station'].dropna().unique().tolist())}")

    print(f"\n  Null % per column:")
    for col in ["pm25", "pm10", "no2", "o3", "wind_speed",
                "wind_direction", "temperature", "humidity",
                "latitude", "longitude"]:
        if col in df.columns:
            pct  = df[col].isna().mean() * 100
            flag = " ⚠" if pct > 25 else ""
            print(f"    {col:<22}: {pct:5.1f}%{flag}")

    print(f"\n  Value ranges:")
    for col, (lo, hi) in [("pm25", (0, 80)), ("pm10", (0, 250)),
                           ("no2",  (0, 200)), ("o3",   (0, 200)),
                           ("wind_speed", (0, 20))]:
        if col in df.columns:
            vals = df[col].dropna()
            if len(vals):
                out = ((vals < lo) | (vals > hi)).mean() * 100
                print(f"    {col:<22}: min={vals.min():.1f}  "
                      f"max={vals.max():.1f}  out-of-range={out:.1f}%")
    print()


# ── Load-or-fetch (called by run_pipeline.py) ─────────────────────────────────

def load_or_fetch(
    filename:    str  = "air_quality_real.csv",
    date_from:   str  = None,
    date_to:     str  = None,
    force_fetch: bool = False,
    use_daily:   bool = False,
    verbose:     bool = True,
) -> pd.DataFrame:
    """
    Load cached real data if it exists, otherwise download and cache it.
    """
    cache_path = os.path.join(BASE_PATH, "raw", filename)

    if not force_fetch and os.path.exists(cache_path):
        if verbose:
            print(f"Loading cached data: {cache_path}")
        df = pd.read_csv(cache_path, parse_dates=["datetime"])
        if verbose:
            print(f"  {len(df):,} rows loaded.")
    else:
        url = DAILY_CSV_URL if use_daily else HOURLY_CSV_URL
        raw = download_csv(url, verbose=verbose)
        df  = parse_and_normalise(raw, verbose=verbose)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df.to_csv(cache_path, index=False)
        if verbose:
            print(f"  Cached → {cache_path}")

    if date_from or date_to:
        df = filter_dates(df, date_from, date_to)
        if verbose:
            print(f"  After date filter: {len(df):,} rows")

    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and cache RVVCCA air quality data from Open Data Valencia"
    )
    parser.add_argument("--from",    dest="date_from", default=None,
                        help="Filter start date YYYY-MM-DD")
    parser.add_argument("--to",      dest="date_to",   default=None,
                        help="Filter end date YYYY-MM-DD")
    parser.add_argument("--force",   action="store_true",
                        help="Re-download even if cache exists")
    parser.add_argument("--daily",   action="store_true",
                        help="Use daily dataset instead of hourly")
    args = parser.parse_args()

    df = load_or_fetch(
        date_from=args.date_from,
        date_to=args.date_to,
        force_fetch=args.force,
        use_daily=args.daily,
    )

    if not df.empty:
        data_quality_report(df)
        print("First 5 rows:")
        print(df.head().to_string())
