import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)

from src.data_extraction.vahan_extractor import VahanDataExtractor
from src.data_processing.data_cleaner import DataProcessor
from src.analytics.growth_calculator import GrowthAnalyzer


@pytest.fixture(scope="session")
def sample_dates():
    end = datetime(2024, 12, 31)
    start = end - timedelta(days=120)
    return pd.date_range(start, end, freq='D')


@pytest.fixture(scope="session")
def sample_raw_state_df(sample_dates):
    states = ["Maharashtra", "Karnataka", "Tamil Nadu"]
    categories = ["2W", "3W", "4W"]
    data = []
    for dt in sample_dates:
        for s in states:
            for c in categories:
                data.append({
                    'date': dt,
                    'state': s,
                    'vehicle_category': c,
                    'registrations': np.random.randint(50, 500)
                })
    return pd.DataFrame(data)


@pytest.fixture(scope="session")
def data_processor():
    return DataProcessor()


@pytest.fixture(scope="session")
def growth_analyzer():
    return GrowthAnalyzer()


@pytest.fixture(scope="session")
def extractor():
    return VahanDataExtractor()
