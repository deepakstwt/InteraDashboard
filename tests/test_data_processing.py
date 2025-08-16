import pandas as pd
import numpy as np

def test_clean_raw_data(data_processor, sample_raw_state_df):
    cleaned = data_processor.clean_raw_data(sample_raw_state_df)
    assert not cleaned.duplicated().any()
    assert cleaned['date'].dtype.kind in ('M', 'm')
    assert (cleaned['registrations'] >= 0).all()


def test_monthly_aggregation(data_processor, sample_raw_state_df):
    cleaned = data_processor.clean_raw_data(sample_raw_state_df)
    monthly = data_processor.aggregate_daily_to_monthly(cleaned, ['state', 'vehicle_category'])
    assert {'date', 'state', 'vehicle_category', 'registrations'} <= set(monthly.columns)
    assert monthly['registrations'].min() >= 0


def test_market_share(data_processor, sample_raw_state_df):
    cleaned = data_processor.clean_raw_data(sample_raw_state_df)
    ms = data_processor.calculate_market_share(cleaned, 'state')
    assert 'market_share' in ms.columns
    grouped = ms.groupby(['date', 'vehicle_category'])['market_share'].sum().round(0)
    assert (grouped.between(95, 105)).all()
