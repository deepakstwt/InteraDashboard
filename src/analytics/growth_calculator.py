import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import ANALYTICS_CONFIG, EXPORTS_DIR


class GrowthAnalyzer:
    
    def __init__(self):
        self.exports_dir = EXPORTS_DIR
        
    def calculate_yoy_growth(self, df: pd.DataFrame, value_col: str = 'registrations', 
                           date_col: str = 'date', group_cols: List[str] = None) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy[date_col] = pd.to_datetime(df_copy[date_col])
        df_copy['year'] = df_copy[date_col].dt.year
        df_copy['month'] = df_copy[date_col].dt.month
        if group_cols is None:
            group_cols = []
        group_by_cols = ['year', 'month'] + group_cols
        monthly_data = df_copy.groupby(group_by_cols)[value_col].sum().reset_index()
        monthly_data = monthly_data.sort_values(['year', 'month'] + group_cols)
        def calc_yoy(group):
            group = group.sort_values(['year', 'month'])
            group['prev_year_value'] = group[value_col].shift(12)
            group['yoy_growth'] = ((group[value_col] - group['prev_year_value']) / group['prev_year_value'] * 100)
            return group
        if group_cols:
            result = monthly_data.groupby(group_cols).apply(calc_yoy).reset_index(drop=True)
        else:
            result = calc_yoy(monthly_data)
        result['date'] = pd.to_datetime(result[['year', 'month']].assign(day=1))
        return result
    
    def calculate_qoq_growth(self, df: pd.DataFrame, value_col: str = 'registrations',
                           date_col: str = 'date', group_cols: List[str] = None) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy[date_col] = pd.to_datetime(df_copy[date_col])
        df_copy['year'] = df_copy[date_col].dt.year
        df_copy['quarter'] = df_copy[date_col].dt.quarter
        if group_cols is None:
            group_cols = []
        group_by_cols = ['year', 'quarter'] + group_cols
        quarterly_data = df_copy.groupby(group_by_cols)[value_col].sum().reset_index()
        quarterly_data = quarterly_data.sort_values(['year', 'quarter'] + group_cols)
        def calc_qoq(group):
            group = group.sort_values(['year', 'quarter'])
            group['prev_quarter_value'] = group[value_col].shift(1)
            group['qoq_growth'] = ((group[value_col] - group['prev_quarter_value']) / group['prev_quarter_value'] * 100)
            return group
        if group_cols:
            result = quarterly_data.groupby(group_cols).apply(calc_qoq).reset_index(drop=True)
        else:
            result = calc_qoq(quarterly_data)
        result['month'] = (result['quarter'] - 1) * 3 + 1
        result['day'] = 1
        result['date'] = pd.to_datetime(result[['year', 'month', 'day']])
        result = result.drop(columns=['month', 'day'])
        return result
    
    def calculate_mom_growth(self, df: pd.DataFrame, value_col: str = 'registrations',
                           date_col: str = 'date', group_cols: List[str] = None) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy[date_col] = pd.to_datetime(df_copy[date_col])
        df_copy['year'] = df_copy[date_col].dt.year
        df_copy['month'] = df_copy[date_col].dt.month
        if group_cols is None:
            group_cols = []
        group_by_cols = ['year', 'month'] + group_cols
        monthly_data = df_copy.groupby(group_by_cols)[value_col].sum().reset_index()
        monthly_data = monthly_data.sort_values(['year', 'month'] + group_cols)
        def calc_mom(group):
            group = group.sort_values(['year', 'month'])
            group['prev_month_value'] = group[value_col].shift(1)
            group['mom_growth'] = ((group[value_col] - group['prev_month_value']) / group['prev_month_value'] * 100)
            return group
        if group_cols:
            result = monthly_data.groupby(group_cols).apply(calc_mom).reset_index(drop=True)
        else:
            result = calc_mom(monthly_data)
        result['date'] = pd.to_datetime(result[['year', 'month']].assign(day=1))
        return result
    
    def calculate_market_share_trends(self, df: pd.DataFrame, entity_col: str,
                                    value_col: str = 'registrations', 
                                    date_col: str = 'date') -> pd.DataFrame:
        df_copy = df.copy()
        df_copy[date_col] = pd.to_datetime(df_copy[date_col])
        df_copy['year_month'] = df_copy[date_col].dt.to_period('M')
        monthly_totals = df_copy.groupby(['year_month', 'vehicle_category'])[value_col].sum().reset_index()
        monthly_totals = monthly_totals.rename(columns={value_col: 'total_monthly_registrations'})
        entity_monthly = df_copy.groupby(['year_month', 'vehicle_category', entity_col])[value_col].sum().reset_index()
        entity_with_totals = entity_monthly.merge(
            monthly_totals,
            on=['year_month', 'vehicle_category'],
            how='left'
        )
        entity_with_totals['market_share'] = (
            entity_with_totals[value_col] / entity_with_totals['total_monthly_registrations'] * 100
        )
        entity_with_totals['date'] = entity_with_totals['year_month'].dt.to_timestamp()
        entity_with_totals = entity_with_totals.drop('year_month', axis=1)
        return entity_with_totals
    
    def identify_growth_leaders(self, df: pd.DataFrame, metric: str = 'yoy_growth',
                              entity_col: str = 'manufacturer', top_n: int = 5) -> Dict[str, pd.DataFrame]:
        latest_date = df['date'].max()
        latest_data = df[df['date'] == latest_date].copy()
        latest_data = latest_data.dropna(subset=[metric])
        entity_growth = latest_data.groupby([entity_col, 'vehicle_category'])[metric].mean().reset_index()
        entity_growth = entity_growth.sort_values(metric, ascending=False)
        results = {}
        for category in entity_growth['vehicle_category'].unique():
            category_data = entity_growth[entity_growth['vehicle_category'] == category]
            results[f'{category}_leaders'] = category_data.head(top_n)
            results[f'{category}_laggards'] = category_data.tail(top_n)
        overall_growth = latest_data.groupby(entity_col)[metric].mean().reset_index()
        overall_growth = overall_growth.sort_values(metric, ascending=False)
        results['overall_leaders'] = overall_growth.head(top_n)
        results['overall_laggards'] = overall_growth.tail(top_n)
        return results
    
    def calculate_volatility_metrics(self, df: pd.DataFrame, value_col: str = 'registrations',
                                   date_col: str = 'date', group_cols: List[str] = None) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy[date_col] = pd.to_datetime(df_copy[date_col])
        if group_cols is None:
            group_cols = []
        def calc_volatility(group):
            group = group.sort_values(date_col)
            group['volatility_30d'] = group[value_col].rolling(window=30).std()
            group['cv_30d'] = group['volatility_30d'] / group[value_col].rolling(window=30).mean()
            rolling_max = group[value_col].rolling(window=30).max()
            drawdown = (group[value_col] - rolling_max) / rolling_max
            group['max_drawdown_30d'] = drawdown.rolling(window=30).min()
            return group
        if group_cols:
            result = df_copy.groupby(group_cols).apply(calc_volatility).reset_index(drop=True)
        else:
            result = calc_volatility(df_copy)
        return result
    
    def generate_investment_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy['investment_signal'] = 'HOLD'
        df_copy['signal_strength'] = 0.0
        df_copy['signal_reasoning'] = ''
        def generate_signal(row):
            signals = []
            score = 0
            reasoning = []
            if 'yoy_growth' in row and pd.notna(row['yoy_growth']):
                if row['yoy_growth'] > 20:
                    signals.append('BUY')
                    score += 2
                    reasoning.append(f"Strong YoY growth: {row['yoy_growth']:.1f}%")
                elif row['yoy_growth'] > 10:
                    signals.append('BUY')
                    score += 1
                    reasoning.append(f"Good YoY growth: {row['yoy_growth']:.1f}%")
                elif row['yoy_growth'] < -10:
                    signals.append('SELL')
                    score -= 2
                    reasoning.append(f"Negative YoY growth: {row['yoy_growth']:.1f}%")
            if 'qoq_growth' in row and pd.notna(row['qoq_growth']):
                if row['qoq_growth'] > 15:
                    signals.append('BUY')
                    score += 1
                    reasoning.append(f"Strong QoQ growth: {row['qoq_growth']:.1f}%")
                elif row['qoq_growth'] < -15:
                    signals.append('SELL')
                    score -= 1
                    reasoning.append(f"Poor QoQ growth: {row['qoq_growth']:.1f}%")
            if 'market_share' in row and pd.notna(row['market_share']):
                if row['market_share'] > 15:
                    signals.append('BUY')
                    score += 1
                    reasoning.append(f"High market share: {row['market_share']:.1f}%")
            if 'cv_30d' in row and pd.notna(row['cv_30d']):
                if row['cv_30d'] > 0.5:
                    score -= 1
                    reasoning.append(f"High volatility (CV: {row['cv_30d']:.2f})")
            if score >= 2:
                final_signal = 'STRONG_BUY'
            elif score >= 1:
                final_signal = 'BUY'
            elif score <= -2:
                final_signal = 'STRONG_SELL'
            elif score <= -1:
                final_signal = 'SELL'
            else:
                final_signal = 'HOLD'
            return final_signal, abs(score), '; '.join(reasoning)
        signal_results = df_copy.apply(generate_signal, axis=1, result_type='expand')
        df_copy['investment_signal'] = signal_results[0]
        df_copy['signal_strength'] = signal_results[1]
        df_copy['signal_reasoning'] = signal_results[2]
        return df_copy
    
    def create_comprehensive_analysis(self, df: pd.DataFrame, entity_col: str = 'manufacturer') -> Dict[str, pd.DataFrame]:
        results = {}
        yoy_data = self.calculate_yoy_growth(df, group_cols=[entity_col, 'vehicle_category'])
        qoq_data = self.calculate_qoq_growth(df, group_cols=[entity_col, 'vehicle_category'])
        mom_data = self.calculate_mom_growth(df, group_cols=[entity_col, 'vehicle_category'])
        market_share_data = self.calculate_market_share_trends(df, entity_col)
        volatility_data = self.calculate_volatility_metrics(df, group_cols=[entity_col, 'vehicle_category'])
        comprehensive_df = df.copy()
        for growth_df, suffix in [(yoy_data, '_yoy'), (qoq_data, '_qoq'), (mom_data, '_mom')]:
            merge_cols = ['date', entity_col, 'vehicle_category']
            growth_cols = [col for col in growth_df.columns if 'growth' in col]
            merge_df = growth_df[merge_cols + growth_cols]
            comprehensive_df = comprehensive_df.merge(merge_df, on=merge_cols, how='left', suffixes=('', suffix))
        market_share_cols = ['date', entity_col, 'vehicle_category', 'market_share']
        if all(col in market_share_data.columns for col in market_share_cols):
            comprehensive_df = comprehensive_df.merge(
                market_share_data[market_share_cols],
                on=['date', entity_col, 'vehicle_category'],
                how='left'
            )
        volatility_cols = [col for col in volatility_data.columns if 'volatility' in col or 'cv_' in col or 'drawdown' in col]
        if volatility_cols:
            merge_volatility = volatility_data[['date', entity_col, 'vehicle_category'] + volatility_cols]
            comprehensive_df = comprehensive_df.merge(
                merge_volatility,
                on=['date', entity_col, 'vehicle_category'],
                how='left'
            )
        comprehensive_df = self.generate_investment_signals(comprehensive_df)
        results['comprehensive'] = comprehensive_df
        results['yoy_analysis'] = yoy_data
        results['qoq_analysis'] = qoq_data
        results['mom_analysis'] = mom_data
        results['market_share_trends'] = market_share_data
        results['volatility_analysis'] = volatility_data
        if 'yoy_growth' in yoy_data.columns:
            results['growth_leaders'] = self.identify_growth_leaders(yoy_data, 'yoy_growth', entity_col)
        return results


def main():
    analyzer = GrowthAnalyzer()
    dates = pd.date_range('2022-01-01', '2023-12-31', freq='D')
    sample_data = []
    manufacturers = ['Hero MotoCorp', 'Honda', 'TVS', 'Bajaj']
    categories = ['2W', '3W', '4W']
    for date in dates:
        for manufacturer in manufacturers:
            for category in categories:
                sample_data.append({
                    'date': date,
                    'manufacturer': manufacturer,
                    'vehicle_category': category,
                    'registrations': np.random.randint(100, 1000)
                })
    sample_df = pd.DataFrame(sample_data)
    print("Testing analytics...")
    analysis_results = analyzer.create_comprehensive_analysis(sample_df, 'manufacturer')
    for key, df in analysis_results.items():
        if isinstance(df, pd.DataFrame):
            print(f"{key}: {len(df)} records")
        else:
            print(f"{key}: {len(df)} sub-analyses")


if __name__ == "__main__":
    main()
