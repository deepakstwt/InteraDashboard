import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import PROCESSED_DATA_DIR, DATA_CONFIG, VEHICLE_CATEGORIES


class DataProcessor:
    
    def __init__(self):
        self.date_format = DATA_CONFIG["date_format"]
        self.processed_dir = PROCESSED_DATA_DIR
        
    def clean_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        cleaned_df = df.copy()
        if 'date' in cleaned_df.columns:
            cleaned_df['date'] = pd.to_datetime(cleaned_df['date'])
        cleaned_df = cleaned_df.drop_duplicates()
        cleaned_df = cleaned_df.fillna(0)
        if 'registrations' in cleaned_df.columns:
            cleaned_df['registrations'] = pd.to_numeric(cleaned_df['registrations'], errors='coerce').fillna(0)
        if 'total_registrations' in cleaned_df.columns:
            cleaned_df['total_registrations'] = pd.to_numeric(cleaned_df['total_registrations'], errors='coerce').fillna(0)
        if 'date' in cleaned_df.columns:
            cleaned_df = cleaned_df.sort_values('date')
        return cleaned_df
    
    def aggregate_daily_to_monthly(self, df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy['year_month'] = df_copy['date'].dt.to_period('M')
        agg_cols = ['year_month'] + group_cols
        if 'registrations' in df_copy.columns:
            monthly_df = df_copy.groupby(agg_cols)['registrations'].sum().reset_index()
        elif 'total_registrations' in df_copy.columns:
            monthly_df = df_copy.groupby(agg_cols)['total_registrations'].sum().reset_index()
            monthly_df = monthly_df.rename(columns={'total_registrations': 'registrations'})
        monthly_df['date'] = monthly_df['year_month'].dt.to_timestamp()
        monthly_df = monthly_df.drop('year_month', axis=1)
        return monthly_df
    
    def aggregate_daily_to_quarterly(self, df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy['year_quarter'] = df_copy['date'].dt.to_period('Q')
        agg_cols = ['year_quarter'] + group_cols
        if 'registrations' in df_copy.columns:
            quarterly_df = df_copy.groupby(agg_cols)['registrations'].sum().reset_index()
        elif 'total_registrations' in df_copy.columns:
            quarterly_df = df_copy.groupby(agg_cols)['total_registrations'].sum().reset_index()
            quarterly_df = quarterly_df.rename(columns={'total_registrations': 'registrations'})
        quarterly_df['date'] = quarterly_df['year_quarter'].dt.to_timestamp()
        quarterly_df = quarterly_df.drop('year_quarter', axis=1)
        return quarterly_df
    
    def calculate_market_share(self, df: pd.DataFrame, group_col: str, date_col: str = 'date') -> pd.DataFrame:
        df_copy = df.copy()
        total_by_date = df_copy.groupby([date_col, 'vehicle_category'])['registrations'].sum().reset_index()
        total_by_date = total_by_date.rename(columns={'registrations': 'total_category_registrations'})
        df_with_total = df_copy.merge(
            total_by_date,
            on=[date_col, 'vehicle_category'],
            how='left'
        )
        df_with_total['market_share'] = (
            df_with_total['registrations'] / df_with_total['total_category_registrations'] * 100
        )
        return df_with_total
    
    def add_moving_averages(self, df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy = df_copy.sort_values('date')
        if 'registrations' in df_copy.columns:
            df_copy[f'ma_{window}d'] = df_copy['registrations'].rolling(window=window).mean()
        return df_copy
    
    def detect_outliers(self, df: pd.DataFrame, column: str = 'registrations', method: str = 'zscore', threshold: float = 3.0) -> pd.DataFrame:
        df_copy = df.copy()
        if method == 'zscore':
            mean = df_copy[column].mean()
            std = df_copy[column].std()
            df_copy['z_score'] = (df_copy[column] - mean) / std
            df_copy['is_outlier'] = abs(df_copy['z_score']) > threshold
        elif method == 'iqr':
            Q1 = df_copy[column].quantile(0.25)
            Q3 = df_copy[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df_copy['is_outlier'] = (df_copy[column] < lower_bound) | (df_copy[column] > upper_bound)
        return df_copy
    
    def process_state_wise_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        cleaned_df = self.clean_raw_data(raw_df)
        df_with_share = self.calculate_market_share(cleaned_df, 'state')
        df_with_ma = self.add_moving_averages(df_with_share)
        processed_df = self.detect_outliers(df_with_ma)
        filename = f"processed_state_wise_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = self.processed_dir / filename
        processed_df.to_csv(filepath, index=False)
        return processed_df
    
    def process_manufacturer_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        cleaned_df = self.clean_raw_data(raw_df)
        df_with_share = self.calculate_market_share(cleaned_df, 'manufacturer')
        df_with_ma = self.add_moving_averages(df_with_share)
        processed_df = self.detect_outliers(df_with_ma)
        filename = f"processed_manufacturer_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = self.processed_dir / filename
        processed_df.to_csv(filepath, index=False)
        return processed_df
    
    def process_category_trends(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        cleaned_df = self.clean_raw_data(raw_df)
        if 'total_registrations' in cleaned_df.columns:
            cleaned_df = cleaned_df.rename(columns={'total_registrations': 'registrations'})
        df_with_ma = self.add_moving_averages(cleaned_df)
        processed_df = self.detect_outliers(df_with_ma)
        filename = f"processed_category_trends_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = self.processed_dir / filename
        processed_df.to_csv(filepath, index=False)
        return processed_df
    
    def create_aggregated_datasets(self, daily_df: pd.DataFrame, group_cols: List[str]) -> Dict[str, pd.DataFrame]:
        results = {}
        results['monthly'] = self.aggregate_daily_to_monthly(daily_df, group_cols)
        results['quarterly'] = self.aggregate_daily_to_quarterly(daily_df, group_cols)
        return results


def main():
    processor = DataProcessor()
    sample_data = {
        'date': pd.date_range('2023-01-01', '2023-12-31', freq='D'),
        'state': np.random.choice(['Maharashtra', 'Karnataka', 'Tamil Nadu'], 365),
        'vehicle_category': np.random.choice(['2W', '3W', '4W'], 365),
        'registrations': np.random.randint(100, 1000, 365)
    }
    sample_df = pd.DataFrame(sample_data)
    print("Testing data processing...")
    processed_df = processor.process_state_wise_data(sample_df)
    print(f"Processed {len(processed_df)} records")
    aggregated = processor.create_aggregated_datasets(processed_df, ['state', 'vehicle_category'])
    print(f"Monthly data: {len(aggregated['monthly'])} records")
    print(f"Quarterly data: {len(aggregated['quarterly'])} records")


if __name__ == "__main__":
    main()
