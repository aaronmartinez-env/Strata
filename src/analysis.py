"""
analysis.py
-----------
Deep statistical analysis of CMPI divergence patterns.
Exports a complete findings JSON that serves as the single source of truth
for the portfolio frontend — no scientific values should be hardcoded elsewhere.

Data flow:
  aeris_processed.csv → run_analysis() → findings.json → inject_findings.py → portfolio HTML

Usage:
  python src/analysis.py
  (also called automatically by run_pipeline.py)
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_PATH

PIPELINE_VERSION = "1.2.0"


def run_analysis(df: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Run full divergence analysis. Returns findings dict — the single source
    of truth for all scientific values displayed in the portfolio.
    """
    findings = {}

    if verbose:
        print("\n── AERIS Deep Analysis ─────────────────────────────")

    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour']  = df['datetime'].dt.hour
    df['month'] = df['datetime'].dt.month
    df['date']  = df['datetime'].dt.date

    aqi_pub_col = 'aqi_public' if 'aqi_public' in df.columns else 'aqi_pub'

    # ── Provenance metadata ───────────────────────────────────────────────────
    findings['provenance'] = {
        'generated_at':      datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
        'pipeline_version':  PIPELINE_VERSION,
        'dataset':           'RVVCCA · rvvcca_d_horarios_2021-2022',
        'source':            'Open Data Valencia · opendata.vlci.valencia.es',
        'licence':           'CC BY 4.0',
        'total_raw_rows':    None,   # set by run_pipeline.py if available
        'valid_rows':        int(len(df)),
        'n_stations':        int(df['station'].nunique()),
        'date_range_start':  str(df['datetime'].min().date()),
        'date_range_end':    str(df['datetime'].max().date()),
        'note': (
            'All scientific values in the portfolio frontend are derived '
            'from this findings export. No values are manually hardcoded.'
        ),
    }

    # ── Overall summary ───────────────────────────────────────────────────────
    div = df['aqi_divergence'].dropna()
    findings['summary'] = {
        'n_obs':             int(len(df)),
        'n_stations':        int(df['station'].nunique()),
        'mean_divergence':   round(float(div.mean()), 4),
        'std_divergence':    round(float(div.std()), 4),
        'median_divergence': round(float(div.median()), 4),
        'max_divergence':    round(float(div.max()), 4),
        'min_divergence':    round(float(div.min()), 4),
        'p25_divergence':    round(float(div.quantile(0.25)), 4),
        'p75_divergence':    round(float(div.quantile(0.75)), 4),
        'pct_over_20':       round(float((div > 20).mean() * 100), 4),
        'pct_over_10':       round(float((div > 10).mean() * 100), 4),
        'calima_hours':      int(df['calima_event'].sum()),
        'mean_aci':          round(float(df['ACI_normalized'].mean()), 4),
        'std_aci':           round(float(df['ACI_normalized'].std()), 4),
        'mean_cmpi':         round(float(df['aqi_scientific'].mean()), 4),
        'mean_public':       round(float(df[aqi_pub_col].mean()), 4),
    }

    if verbose:
        s = findings['summary']
        print(f"\n[Summary]")
        print(f"  Observations    : {s['n_obs']:,}")
        print(f"  Mean divergence : {s['mean_divergence']:.4f} ± {s['std_divergence']:.4f}")
        print(f"  Max divergence  : {s['max_divergence']:.4f}")
        print(f"  Calima hours    : {s['calima_hours']:,}")
        print(f"  Mean ACI        : {s['mean_aci']:.4f}")

    # ── Diurnal pattern ───────────────────────────────────────────────────────
    hourly = df.groupby('hour').agg(
        aqi_divergence=('aqi_divergence', 'mean'),
        aqi_divergence_std=('aqi_divergence', 'std'),
        no2=('no2', 'mean'),
        o3=('o3', 'mean'),
        wind_speed=('wind_speed', 'mean'),
        temperature=('temperature', 'mean'),
        n=('aqi_divergence', 'count'),
    ).round(4).reset_index()

    peak_idx = hourly['aqi_divergence'].idxmax()
    min_idx  = hourly['aqi_divergence'].idxmin()

    findings['diurnal'] = {
        'hourly':            hourly.to_dict('records'),
        'peak_hour':         int(hourly.loc[peak_idx, 'hour']),
        'min_hour':          int(hourly.loc[min_idx, 'hour']),
        'peak_divergence':   round(float(hourly['aqi_divergence'].max()), 4),
        'min_divergence':    round(float(hourly['aqi_divergence'].min()), 4),
        'intraday_swing':    round(float(hourly['aqi_divergence'].max() - hourly['aqi_divergence'].min()), 4),
        'hours_available':   int(df['hour'].nunique()),
        'divergence_array':  [round(float(v), 4) for v in hourly.sort_values('hour')['aqi_divergence']],
    }

    if verbose:
        d = findings['diurnal']
        print(f"\n[Diurnal]")
        print(f"  Peak : {d['peak_divergence']:.4f} at {d['peak_hour']:02d}:00")
        print(f"  Min  : {d['min_divergence']:.4f} at {d['min_hour']:02d}:00")
        print(f"  Swing: {d['intraday_swing']:.4f}")

    # ── Per-station aggregates ────────────────────────────────────────────────
    # Everything needed by the frontend STATIONS array
    st_agg = df.groupby('station').agg(
        latitude        =('latitude',        'first'),
        longitude       =('longitude',       'first'),
        pm10_mean       =('pm10',            'mean'),
        pm10_max        =('pm10',            'max'),
        pm25_mean       =('pm25',            'mean'),
        pm25_max        =('pm25',            'max'),
        no2_mean        =('no2',             'mean'),
        no2_max         =('no2',             'max'),
        o3_mean         =('o3',              'mean'),
        o3_max          =('o3',              'max'),
        cmpi_mean       =('aqi_scientific',  'mean'),
        cmpi_max        =('aqi_scientific',  'max'),
        public_mean     =(aqi_pub_col,       'mean'),
        aqi_div_mean    =('aqi_divergence',  'mean'),
        aqi_div_max     =('aqi_divergence',  'max'),
        aqi_div_std     =('aqi_divergence',  'std'),
        calima_hours    =('calima_event',    'sum'),
        aci_mean        =('ACI_normalized',  'mean'),
        n_obs           =('aqi_divergence',  'count'),
    ).reset_index().round(4)

    st_agg['calima_hours'] = st_agg['calima_hours'].astype(int)
    st_agg['n_obs']        = st_agg['n_obs'].astype(int)

    findings['stations'] = (
        st_agg.sort_values('aqi_div_mean', ascending=False)
        .to_dict('records')
    )

    if verbose:
        print(f"\n[Stations — ranked by mean divergence]")
        for r in findings['stations']:
            print(f"  {r['station']:<26} "
                  f"div={r['aqi_div_mean']:.3f}  "
                  f"PM10={r['pm10_mean']:.1f}  "
                  f"NO2={r['no2_mean']:.1f}  "
                  f"calima={r['calima_hours']}h")

    # ── Correlations ──────────────────────────────────────────────────────────
    pred_cols = ['no2', 'temperature', 'pm25', 'ACI_normalized',
                 'pm10', 'o3', 'wind_speed', 'humidity']
    available = [c for c in pred_cols if c in df.columns]
    corr = (df[available + ['aqi_divergence']]
            .corr()['aqi_divergence']
            .drop('aqi_divergence')
            .sort_values(key=abs, ascending=False))

    findings['correlations'] = {
        col: round(float(val), 4) for col, val in corr.items()
    }

    if verbose:
        print(f"\n[Correlations with CMPI divergence]")
        for col, val in findings['correlations'].items():
            bar = '█' * int(abs(val) * 20)
            print(f"  {col:<22} {'+' if val >= 0 else ''}{val:.4f}  {bar}")

    # ── NO₂ quartile analysis ─────────────────────────────────────────────────
    df['no2_q'] = pd.qcut(df['no2'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    no2_q = df.groupby('no2_q', observed=True).agg(
        mean_div   =('aqi_divergence', 'mean'),
        std_div    =('aqi_divergence', 'std'),
        mean_no2   =('no2',           'mean'),
        n          =('aqi_divergence', 'count'),
    ).round(4).reset_index()

    findings['no2_quartiles'] = {
        'labels':     ['Q1 (low NO₂)', 'Q2', 'Q3', 'Q4 (high NO₂)'],
        'divergence': no2_q['mean_div'].tolist(),
        'no2_means':  no2_q['mean_no2'].tolist(),
        'counts':     no2_q['n'].tolist(),
        'std':        no2_q['std_div'].tolist(),
    }

    # ── Air mass regime ───────────────────────────────────────────────────────
    am = df.groupby('air_mass_type').agg(
        mean_div  =('aqi_divergence', 'mean'),
        std_div   =('aqi_divergence', 'std'),
        mean_no2  =('no2',           'mean'),
        mean_wind =('wind_speed',    'mean'),
        count     =('aqi_divergence', 'count'),
        pct       =('aqi_divergence', 'count'),
    ).reset_index()
    am['pct'] = (am['pct'] / len(df) * 100).round(2)
    am = am.round(4)

    findings['air_mass'] = am.to_dict('records')

    if verbose:
        print(f"\n[Air mass divergence]")
        for _, r in am.iterrows():
            print(f"  {r['air_mass_type']:<18} "
                  f"div={r['mean_div']:.3f}±{r['std_div']:.3f}  "
                  f"n={r['count']:,}  pct={r['pct']:.1f}%")

    # ── Calima episode analysis ───────────────────────────────────────────────
    cal  = df[df['calima_event'] == True]
    norm = df[df['calima_event'] == False]

    if len(cal) > 0:
        # "over-read" = public index > CMPI for the same station-hour during calima
        cal_over = (cal[aqi_pub_col] > cal['aqi_scientific']).sum()
        cal_pct  = float(cal_over) / len(cal) * 100

        findings['calima'] = {
            'n_hours':                int(len(cal)),
            'pct_of_valid_obs':       round(float(len(cal)) / len(df) * 100, 4),
            'pct_public_over':        round(cal_pct, 2),
            'over_read_definition':   (
                'Cases where public PM10-only index score exceeded '
                'the CMPI score for the same station-hour during a '
                'confirmed calima event (dual-criterion: PM10 > 72h '
                'rolling mean + 1.5σ AND PM10/PM2.5 ratio > 3.0)'
            ),
            'mean_public_aqi':        round(float(cal[aqi_pub_col].mean()), 4),
            'mean_cmpi':              round(float(cal['aqi_scientific'].mean()), 4),
            'mean_divergence':        round(float(cal['aqi_divergence'].mean()), 4),
            'max_pm10_hourly':        round(float(cal['pm10'].max()), 2),
            'mean_dust_ratio':        round(float((cal['pm10'] / (cal['pm25'] + 1e-6)).mean()), 4),
            'normal_divergence':      round(float(norm['aqi_divergence'].mean()), 4),
            # Which station recorded the max PM10, and when
            'max_pm10_station':       df.loc[df['pm10'].idxmax(), 'station'],
            'max_pm10_datetime':      str(df.loc[df['pm10'].idxmax(), 'datetime']),
        }

        if verbose:
            c = findings['calima']
            print(f"\n[Calima]")
            print(f"  Hours           : {c['n_hours']:,} ({c['pct_of_valid_obs']:.2f}%)")
            print(f"  Public > CMPI   : {c['pct_public_over']:.1f}% of calima hours")
            print(f"  Max PM10 hourly : {c['max_pm10_hourly']:.1f} µg/m³ "
                  f"at {c['max_pm10_station']} on {c['max_pm10_datetime'][:10]}")
    else:
        findings['calima'] = {'n_hours': 0}

    # ── Nocturnal stagnation ──────────────────────────────────────────────────
    noc = df[df['hour'].between(0, 8) & (df['air_mass_type'] == 'stagnant_mix')]
    day = df[df['hour'].between(11, 16)]

    findings['nocturnal'] = {
        'mean_divergence': round(float(noc['aqi_divergence'].mean()), 4) if len(noc) else None,
        'mean_no2':        round(float(noc['no2'].mean()), 4) if len(noc) else None,
        'n_obs':           int(len(noc)),
        'day_divergence':  round(float(day['aqi_divergence'].mean()), 4) if len(day) else None,
        'day_no2':         round(float(day['no2'].mean()), 4) if len(day) else None,
    }

    # ── Daily aggregates (for time-series charts) ─────────────────────────────
    daily = df.groupby('date').agg(
        pm10    =('pm10',           'mean'),
        pm25    =('pm25',           'mean'),
        no2     =('no2',            'mean'),
        o3      =('o3',             'mean'),
        aqi_sci =('aqi_scientific', 'mean'),
        aqi_pub =(aqi_pub_col,      'mean'),
        aqi_div =('aqi_divergence', 'mean'),
        calima  =('calima_event',   'sum'),
        aci     =('ACI_normalized', 'mean'),
        n       =('aqi_divergence', 'count'),
    ).reset_index().round(4)
    daily['date'] = daily['date'].astype(str)

    findings['daily'] = daily.to_dict('records')

    # ── PM10 overall stats ────────────────────────────────────────────────────
    pm10_all = df['pm10'].dropna()
    findings['pm10_stats'] = {
        'mean':       round(float(pm10_all.mean()), 4),
        'max_hourly': round(float(pm10_all.max()), 2),
        'p95':        round(float(pm10_all.quantile(0.95)), 2),
        'p99':        round(float(pm10_all.quantile(0.99)), 2),
        'max_station': df.loc[df['pm10'].idxmax(), 'station'],
        'max_datetime': str(df.loc[df['pm10'].idxmax(), 'datetime']),
        'who_exceedances_24h': None,  # would need daily averages per station
    }

    if verbose:
        print(f"\n[PM10]")
        print(f"  Max hourly: {findings['pm10_stats']['max_hourly']:.1f} µg/m³ "
              f"at {findings['pm10_stats']['max_station']} "
              f"({findings['pm10_stats']['max_datetime'][:10]})")

    if verbose:
        print(f"\n✓ Analysis complete — {len(findings)} finding categories.")

    return findings


def save_findings(findings: dict, filename: str = 'aeris_findings.json') -> str:
    os.makedirs(os.path.join(OUTPUT_PATH, 'reports'), exist_ok=True)
    path = os.path.join(OUTPUT_PATH, 'reports', filename)
    with open(path, 'w') as f:
        json.dump(findings, f, indent=2, default=str)
    print(f"  Findings saved → {path}")
    return path


def print_research_summary(findings: dict) -> None:
    print("\n" + "=" * 52)
    print("  AERIS — Research Question Summary")
    print("=" * 52)
    s  = findings['summary']
    d  = findings['diurnal']
    c  = findings.get('calima', {})
    cr = findings['correlations']
    pm = findings['pm10_stats']

    print(f"\n  Q: How accurately do public AQI representations")
    print(f"     reflect atmospheric conditions in Valencia?\n")
    print(f"  Observations    : {s['n_obs']:,}")
    print(f"  Stations        : {s['n_stations']}")
    print(f"  Date range      : {findings['provenance']['date_range_start']} "
          f"→ {findings['provenance']['date_range_end']}")
    print(f"\n  Mean CMPI gap   : {s['mean_divergence']:.4f} index pts")
    print(f"  Max CMPI gap    : {s['max_divergence']:.4f} index pts")
    print(f"  Peak hour       : {d['peak_hour']:02d}:00 "
          f"(gap = {d['peak_divergence']:.4f} pts)")
    print(f"  Min hour        : {d['min_hour']:02d}:00 "
          f"(gap = {d['min_divergence']:.4f} pts)")
    print(f"  Primary correlate: NO₂ (r = {cr.get('no2', '?')})")
    print(f"  Calima hours    : {c.get('n_hours', 0):,} "
          f"({c.get('pct_of_valid_obs', 0):.2f}% of obs)")
    if c.get('n_hours', 0) > 0:
        print(f"  Public > CMPI   : {c.get('pct_public_over', '?'):.1f}% of calima hours")
    print(f"  Max hourly PM10 : {pm['max_hourly']:.1f} µg/m³ "
          f"at {pm['max_station']} ({pm['max_datetime'][:10]})")
    print(f"  Mean ACI        : {s['mean_aci']:.4f}")
    print(f"\n  Generated: {findings['provenance']['generated_at']}")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    processed_path = os.path.join(
        os.path.dirname(__file__), '../data/processed/aeris_processed.csv'
    )
    if not os.path.exists(processed_path):
        print(f"No processed data at {processed_path}")
        print("Run: python src/run_pipeline.py")
        sys.exit(1)
    df = pd.read_csv(processed_path, parse_dates=['datetime'])
    findings = run_analysis(df, verbose=True)
    print_research_summary(findings)
    save_findings(findings)
