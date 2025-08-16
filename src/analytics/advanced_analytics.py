"""Advanced analytics scaffolding: anomaly detection & forecasting.
Minimal, dependency-light (uses statsmodels if available) so dashboard can call safely.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing  # lightweight forecasting
    _HAS_STATSMODELS = True
except Exception:
    _HAS_STATSMODELS = False

# ---------------- Anomaly Detection -----------------

def detect_anomalies(
    df: pd.DataFrame,
    value_col: str = "registrations",
    entity_cols: Optional[List[str]] = None,
    date_col: str = "date",
    z_thresh: float = 3.0,
    rolling_window: int = 7,
) -> pd.DataFrame:
    """Flag point anomalies using rolling mean/std z-score.
    Adds columns: rolling_mean, rolling_std, z_score, is_anomaly.
    """
    if entity_cols is None:
        entity_cols = []
    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col])
    group_cols = entity_cols if entity_cols else [None]
    results = []
    for key, g in (work.groupby(entity_cols) if entity_cols else [(None, work)]):
        g = g.sort_values(date_col)
        g["rolling_mean"] = g[value_col].rolling(rolling_window, min_periods=rolling_window//2).mean()
        g["rolling_std"] = g[value_col].rolling(rolling_window, min_periods=rolling_window//2).std()
        g["z_score"] = (g[value_col] - g["rolling_mean"]) / g["rolling_std"]
        g["is_anomaly"] = g["z_score"].abs() > z_thresh
        results.append(g)
    out = pd.concat(results, ignore_index=True)
    return out

# ---------------- Forecasting -----------------

def forecast_category(
    df: pd.DataFrame,
    category: str,
    periods: int = 30,
    value_col: str = "registrations",
    date_col: str = "date",
    season_length: int = 7,
) -> pd.DataFrame:
    """Produce simple additive Holt-Winters forecast for a given vehicle_category.
    Returns DataFrame with columns: date, vehicle_category, forecast, lower, upper.
    Falls back to seasonal naive if statsmodels unavailable or model fails.
    """
    cat_df = df[df.get("vehicle_category") == category].copy()
    if cat_df.empty:
        return pd.DataFrame(columns=["date", "vehicle_category", "forecast", "lower", "upper"])
    cat_df[date_col] = pd.to_datetime(cat_df[date_col])
    daily = cat_df.groupby(date_col)[value_col].sum().asfreq('D')
    if len(daily) < season_length * 2:
        # not enough data
        return _naive_forecast(daily, category, periods)
    if not _HAS_STATSMODELS:
        return _naive_forecast(daily, category, periods)
    try:
        model = ExponentialSmoothing(
            daily,
            seasonal_periods=season_length,
            trend='add',
            seasonal='add',
            initialization_method='estimated'
        ).fit(optimized=True)
        fc = model.forecast(periods)
        resid_std = np.nanstd(model.resid)
        idx = fc.index
        df_fc = pd.DataFrame({
            'date': idx,
            'vehicle_category': category,
            'forecast': fc.values,
            'lower': fc.values - 1.96 * resid_std,
            'upper': fc.values + 1.96 * resid_std
        })
        return df_fc
    except Exception:
        return _naive_forecast(daily, category, periods)

def _naive_forecast(series: pd.Series, category: str, periods: int) -> pd.DataFrame:
    if series.empty:
        future_idx = pd.date_range(datetime.utcnow().date(), periods=periods, freq='D')
        return pd.DataFrame({'date': future_idx, 'vehicle_category': category, 'forecast': 0, 'lower': 0, 'upper': 0})
    last_cycle = series[-min(len(series), 7):]
    reps = int(np.ceil(periods / len(last_cycle)))
    vals = np.tile(last_cycle.values, reps)[:periods]
    future_idx = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=periods, freq='D')
    return pd.DataFrame({
        'date': future_idx,
        'vehicle_category': category,
        'forecast': vals,
        'lower': vals * 0.9,
        'upper': vals * 1.1
    })

# ---------------- Batch Helper -----------------

def batch_forecast(df: pd.DataFrame, categories: List[str], periods: int = 30) -> Dict[str, pd.DataFrame]:
    return {c: forecast_category(df, c, periods=periods) for c in categories}

__all__ = [
    'detect_anomalies',
    'forecast_category',
    'batch_forecast'
]
