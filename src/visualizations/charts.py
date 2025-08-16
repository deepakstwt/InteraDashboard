import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.figure_factory as ff
except ImportError:
    print("Plotly not installed. Run: pip install plotly")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import VEHICLE_CATEGORIES, DASHBOARD_CONFIG


class VehicleDataVisualizer:
    
    def __init__(self):
        self.color_palette = {
            "2W": "#FF6B6B",
            "3W": "#4ECDC4", 
            "4W": "#45B7D1",
            "positive": "#2ECC71",
            "negative": "#E74C3C",
            "neutral": "#95A5A6"
        }
        
    def create_registration_trends_chart(self, df: pd.DataFrame, title: str = "Vehicle Registration Trends") -> go.Figure:
        fig = go.Figure()
        if 'vehicle_category' in df.columns:
            for category in df['vehicle_category'].unique():
                category_data = df[df['vehicle_category'] == category]
                daily_data = category_data.groupby('date')['registrations'].sum().reset_index()
                fig.add_trace(go.Scatter(
                    x=daily_data['date'],
                    y=daily_data['registrations'],
                    mode='lines+markers',
                    name=category,
                    line=dict(color=self.color_palette.get(category, "#666666"), width=3),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{category}</b><br>' +
                                 'Date: %{x}<br>' +
                                 'Registrations: %{y:,.0f}<br>' +
                                 '<extra></extra>'
                ))
        else:
            daily_data = df.groupby('date')['registrations'].sum().reset_index()
            fig.add_trace(go.Scatter(
                x=daily_data['date'],
                y=daily_data['registrations'],
                mode='lines+markers',
                name='Total Registrations',
                line=dict(color=self.color_palette["4W"], width=3),
                marker=dict(size=6)
            ))
        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=20)),
            xaxis_title="Date",
            yaxis_title="Registrations",
            hovermode='x unified',
            template='plotly_white',
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        return fig
    
    def create_growth_metrics_chart(self, df: pd.DataFrame, metric: str = 'yoy_growth') -> go.Figure:
        latest_date = df['date'].max()
        latest_data = df[df['date'] == latest_date].dropna(subset=[metric])
        if latest_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No growth data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            return fig
        entity_col = None
        for col in ['manufacturer', 'state', 'entity']:
            if col in latest_data.columns:
                entity_col = col
                break
        if entity_col is None:
            entity_col = 'vehicle_category'
        plot_data = latest_data.sort_values(metric, ascending=True)
        colors = ['#2ECC71' if x >= 0 else '#E74C3C' for x in plot_data[metric]]
        fig = go.Figure(data=[
            go.Bar(
                y=plot_data[entity_col],
                x=plot_data[metric],
                orientation='h',
                marker_color=colors,
                text=[f"{x:.1f}%" for x in plot_data[metric]],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>' +
                             f'{metric.replace("_", " ").title()}: %{{x:.1f}}%<br>' +
                             '<extra></extra>'
            )
        ])
        metric_title = metric.replace('_', ' ').title()
        fig.update_layout(
            title=dict(text=f"{metric_title} by {entity_col.title()}", x=0.5, font=dict(size=18)),
            xaxis_title=f"{metric_title} (%)",
            yaxis_title=entity_col.title(),
            template='plotly_white',
            height=max(400, len(plot_data) * 30),
            showlegend=False
        )
        fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="black", opacity=0.5)
        return fig
    
    def create_market_share_pie_chart(self, df: pd.DataFrame, category: str = None) -> go.Figure:
        if category and 'vehicle_category' in df.columns:
            df_filtered = df[df['vehicle_category'] == category]
            title_suffix = f" - {category}"
        else:
            df_filtered = df
            title_suffix = ""
        latest_date = df_filtered['date'].max()
        latest_data = df_filtered[df_filtered['date'] == latest_date]
        entity_col = None
        for col in ['manufacturer', 'state']:
            if col in latest_data.columns:
                entity_col = col
                break
        if entity_col is None:
            return go.Figure()
        if 'market_share' in latest_data.columns:
            share_data = latest_data.groupby(entity_col)['market_share'].mean().reset_index()
        else:
            total_registrations = latest_data['registrations'].sum()
            share_data = latest_data.groupby(entity_col)['registrations'].sum().reset_index()
            share_data['market_share'] = share_data['registrations'] / total_registrations * 100
        share_data = share_data.sort_values('market_share', ascending=False)
        fig = go.Figure(data=[
            go.Pie(
                labels=share_data[entity_col],
                values=share_data['market_share'],
                hole=0.3,
                textinfo='label+percent',
                textposition='outside',
                marker=dict(line=dict(color='#FFFFFF', width=2)),
                hovertemplate='<b>%{label}</b><br>' +
                             'Market Share: %{value:.1f}%<br>' +
                             '<extra></extra>'
            )
        ])
        fig.update_layout(
            title=dict(text=f"Market Share{title_suffix}", x=0.5, font=dict(size=18)),
            template='plotly_white',
            height=500,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.01
            )
        )
        return fig
    
    def create_heatmap(self, df: pd.DataFrame, value_col: str = 'registrations') -> go.Figure:
        if 'state' in df.columns and 'vehicle_category' in df.columns:
            pivot_data = df.groupby(['state', 'vehicle_category'])[value_col].sum().unstack(fill_value=0)
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='Blues',
                hoverongaps=False,
                hovertemplate='State: %{y}<br>' +
                             'Category: %{x}<br>' +
                             f'{value_col.title()}: %{{z:,.0f}}<br>' +
                             '<extra></extra>'
            ))
            fig.update_layout(
                title=dict(text=f"{value_col.title()} by State and Category", x=0.5),
                xaxis_title="Vehicle Category",
                yaxis_title="State"
            )
        elif 'manufacturer' in df.columns and 'vehicle_category' in df.columns:
            pivot_data = df.groupby(['manufacturer', 'vehicle_category'])[value_col].sum().unstack(fill_value=0)
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='Blues',
                hoverongaps=False,
                hovertemplate='Manufacturer: %{y}<br>' +
                             'Category: %{x}<br>' +
                             f'{value_col.title()}: %{{z:,.0f}}<br>' +
                             '<extra></extra>'
            ))
            fig.update_layout(
                title=dict(text=f"{value_col.title()} by Manufacturer and Category", x=0.5),
                xaxis_title="Vehicle Category",
                yaxis_title="Manufacturer"
            )
        else:
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date'])
            df_copy['year'] = df_copy['date'].dt.year
            df_copy['month'] = df_copy['date'].dt.month
            pivot_data = df_copy.groupby(['year', 'month'])[value_col].sum().unstack(fill_value=0)
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=[month_names[i-1] for i in pivot_data.columns],
                y=pivot_data.index,
                colorscale='Blues',
                hoverongaps=False,
                hovertemplate='Year: %{y}<br>' +
                             'Month: %{x}<br>' +
                             f'{value_col.title()}: %{{z:,.0f}}<br>' +
                             '<extra></extra>'
            ))
            fig.update_layout(
                title=dict(text=f"{value_col.title()} by Year and Month", x=0.5),
                xaxis_title="Month",
                yaxis_title="Year"
            )
        fig.update_layout(
            template='plotly_white',
            height=500
        )
        return fig
    
    def create_comparison_chart(self, df: pd.DataFrame, entities: List[str], 
                              entity_col: str = 'manufacturer') -> go.Figure:
        filtered_df = df[df[entity_col].isin(entities)]
        fig = go.Figure()
        for entity in entities:
            entity_data = filtered_df[filtered_df[entity_col] == entity]
            if 'vehicle_category' in entity_data.columns:
                daily_data = entity_data.groupby(['date', 'vehicle_category'])['registrations'].sum().reset_index()
                for category in daily_data['vehicle_category'].unique():
                    category_data = daily_data[daily_data['vehicle_category'] == category]
                    fig.add_trace(go.Scatter(
                        x=category_data['date'],
                        y=category_data['registrations'],
                        mode='lines+markers',
                        name=f"{entity} - {category}",
                        line=dict(width=2),
                        marker=dict(size=4),
                        hovertemplate=f'<b>{entity} - {category}</b><br>' +
                                     'Date: %{x}<br>' +
                                     'Registrations: %{y:,.0f}<br>' +
                                     '<extra></extra>'
                    ))
            else:
                daily_data = entity_data.groupby('date')['registrations'].sum().reset_index()
                fig.add_trace(go.Scatter(
                    x=daily_data['date'],
                    y=daily_data['registrations'],
                    mode='lines+markers',
                    name=entity,
                    line=dict(width=3),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{entity}</b><br>' +
                                 'Date: %{x}<br>' +
                                 'Registrations: %{y:,.0f}<br>' +
                                 '<extra></extra>'
                ))
        fig.update_layout(
            title=dict(text=f"{entity_col.title()} Comparison", x=0.5, font=dict(size=18)),
            xaxis_title="Date",
            yaxis_title="Registrations",
            hovermode='x unified',
            template='plotly_white',
            height=500,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.01
            )
        )
        return fig
    
    def create_investment_dashboard(self, df: pd.DataFrame) -> Dict[str, go.Figure]:
        charts = {}
        charts['trends'] = self.create_registration_trends_chart(df, "Vehicle Registration Trends")
        if 'yoy_growth' in df.columns:
            charts['yoy_growth'] = self.create_growth_metrics_chart(df, 'yoy_growth')
        if 'qoq_growth' in df.columns:
            charts['qoq_growth'] = self.create_growth_metrics_chart(df, 'qoq_growth')
        charts['market_share'] = self.create_market_share_pie_chart(df)
        charts['heatmap'] = self.create_heatmap(df)
        if 'investment_signal' in df.columns:
            signal_summary = df.groupby('investment_signal').size().reset_index()
            signal_summary.columns = ['Signal', 'Count']
            charts['signals'] = go.Figure(data=[
                go.Bar(
                    x=signal_summary['Signal'],
                    y=signal_summary['Count'],
                    marker_color=['#E74C3C' if 'SELL' in signal else '#2ECC71' if 'BUY' in signal else '#95A5A6' 
                                 for signal in signal_summary['Signal']]
                )
            ])
            charts['signals'].update_layout(
                title="Investment Signals Distribution",
                xaxis_title="Signal",
                yaxis_title="Count",
                template='plotly_white'
            )
        return charts


def main():
    visualizer = VehicleDataVisualizer()
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    sample_data = []
    manufacturers = ['Hero MotoCorp', 'Honda', 'TVS']
    categories = ['2W', '3W', '4W']
    for date in dates:
        for manufacturer in manufacturers:
            for category in categories:
                sample_data.append({
                    'date': date,
                    'manufacturer': manufacturer,
                    'vehicle_category': category,
                    'registrations': np.random.randint(100, 1000),
                    'yoy_growth': np.random.normal(10, 15),
                    'market_share': np.random.uniform(5, 25)
                })
    sample_df = pd.DataFrame(sample_data)
    print("Testing visualizations...")
    trends_chart = visualizer.create_registration_trends_chart(sample_df)
    growth_chart = visualizer.create_growth_metrics_chart(sample_df, 'yoy_growth')
    market_share_chart = visualizer.create_market_share_pie_chart(sample_df, '2W')
    print("Charts created successfully!")
    print(f"Trends chart: {type(trends_chart)}")
    print(f"Growth chart: {type(growth_chart)}")
    print(f"Market share chart: {type(market_share_chart)}")


if __name__ == "__main__":
    main()
