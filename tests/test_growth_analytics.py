import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _build_sample_growth_df():
    dates = pd.date_range('2024-01-01', '2024-06-30', freq='D')
    manufacturers = ['Hero MotoCorp', 'Honda']
    categories = ['2W', '4W']
    rows = []
    for dt in dates:
        for m in manufacturers:
            for c in categories:
                rows.append({
                    'date': dt,
                    'manufacturer': m,
                    'vehicle_category': c,
                    'registrations': np.random.randint(50, 400)
                })
    return pd.DataFrame(rows)


def test_yoy_growth(growth_analyzer):
    df = _build_sample_growth_df()
    yoy = growth_analyzer.calculate_yoy_growth(df, group_cols=['manufacturer', 'vehicle_category'])
    assert 'yoy_growth' in yoy.columns


def test_qoq_growth(growth_analyzer):
    df = _build_sample_growth_df()
    qoq = growth_analyzer.calculate_qoq_growth(df, group_cols=['manufacturer', 'vehicle_category'])
    assert 'qoq_growth' in qoq.columns


def test_volatility(growth_analyzer):
    df = _build_sample_growth_df()
    vol = growth_analyzer.calculate_volatility_metrics(df, group_cols=['manufacturer', 'vehicle_category'])
    assert {'volatility_30d', 'cv_30d', 'max_drawdown_30d'} <= set(vol.columns)
