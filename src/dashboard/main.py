import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import sys
import os
import hashlib
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from src.data_extraction.vahan_extractor import VahanDataExtractor
    from src.data_processing.data_cleaner import DataProcessor
    from src.analytics.growth_calculator import GrowthAnalyzer
    from src.visualizations.charts import VehicleDataVisualizer
    from src.utils.exporter import build_export_payload
    from src.utils import exporter as _export_mod
    from config import settings as SETTINGS
    from config.settings import DASHBOARD_CONFIG, VEHICLE_CATEGORIES, MAJOR_MANUFACTURERS, EXPORT_CONFIG
except ImportError as e:
    st.error(f"Critical import error: {e}")
    st.stop()

if hasattr(SETTINGS, 'CACHE_DIR'):
    CACHE_DIR = SETTINGS.CACHE_DIR
else:
    CACHE_DIR = getattr(SETTINGS, 'DATA_DIR', Path(__file__).resolve().parents[2] / 'data') / 'cache'
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    setattr(SETTINGS, 'CACHE_DIR', CACHE_DIR)

PDF_AVAILABLE = getattr(_export_mod, 'PDF_AVAILABLE', True)

CACHE_VERSION = "v1"

def _cache_key(prefix: str, *parts) -> str:
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]
    return f"{prefix}_{h}_{CACHE_VERSION}"

@st.cache_data(show_spinner=False, ttl=3600)
def load_or_generate_sample(start: date, end: date, categories: List[str], states: List[str]) -> pd.DataFrame:
    dash = VehicleDashboard._get_singleton()
    return dash._generate_sample_dataframe(start, end, categories, states)

class VehicleDashboard:
    _singleton = None

    @classmethod
    def _get_singleton(cls):
        return cls._singleton

    def __init__(self):
        VehicleDashboard._singleton = self
        if 'ui_theme' not in st.session_state:
            st.session_state['ui_theme'] = 'Light'
        self.setup_page_config()
        self.initialize_components()
        try:
            self.file_cache_dir = Path(CACHE_DIR)
            self.file_cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.file_cache_dir = Path(__file__).resolve().parents[2] / 'data' / 'cache'
            self.file_cache_dir.mkdir(parents=True, exist_ok=True)
        self.apply_theme(st.session_state['ui_theme'])

    def apply_theme(self, mode: str):
        light = (mode == 'Light')
        colors = {
            'bg': '#FFFFFF' if light else '#0E1117',
            'bg2': '#F5F7FA' if light else '#1E222A',
            'text': '#1C1C1C' if light else '#F5F7FA',
            'accent': '#1f77b4',
            'border': '#E0E6ED' if light else '#2A2F36',
            'shadow': '0 2px 4px rgba(0,0,0,0.06)' if light else '0 2px 4px rgba(0,0,0,0.45)'
        }
        style_block = f"""
        <style id="theme-{mode.lower()}">
        :root {{
            --bg: {colors['bg']};
            --bg-alt: {colors['bg2']};
            --text: {colors['text']};
            --accent: {colors['accent']};
            --border: {colors['border']};
            --shadow: {colors['shadow']};
        }}
        html, body, .stApp, [data-testid="stAppViewContainer"], .block-container {{ background: var(--bg) !important; color: var(--text) !important; }}
        [data-testid="stHeader"], [data-testid="stToolbar"] {{ background: var(--bg) !important; }}
        [data-testid="stSidebar"] {{ background: var(--bg-alt) !important; color: var(--text) !important; }}
        .stMarkdown, .stText, .stCheckbox, .stSelectbox, .stRadio, label, p, span, div {{ color: var(--text) !important; }}
        .main-header {{ color: var(--text) !important; }}
        .stMetric label, .stMetric span {{ color: var(--text) !important; }}
        .metric-card, .chart-container, .kpi-card {{
            background: var(--bg-alt) !important; border:1px solid var(--border) !important; box-shadow: var(--shadow) !important;
        }}
        /* FORM / INPUT WIDGET BACKGROUNDS */
        .stSelectbox, .stMultiSelect, .stDateInput, .stRadio, .stNumberInput, .stTextInput, .stDownloadButton, .stFileUploader {{
            background: var(--bg-alt) !important; border-radius: 10px !important; padding: .25rem .5rem !important;
        }}
        .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
            background: var(--bg-alt) !important; color: var(--text) !important; border:1px solid var(--border)!important;
        }}
        .stSelectbox svg, .stMultiSelect svg {{ fill: var(--text) !important; }}
        .stButton button, .stDownloadButton button {{
            background: var(--bg-alt) !important; color: var(--text) !important; border:1px solid var(--border)!important; box-shadow: var(--shadow)!important;
        }}
        .stButton button:hover, .stDownloadButton button:hover {{ border-color: var(--accent)!important; box-shadow: 0 0 0 1px var(--accent) inset !important; }}
        /* BaseWeb popover (dropdown menu) portal */
        div[data-baseweb="popover"] {{ background: var(--bg-alt)!important; border:1px solid var(--border)!important; color: var(--text)!important; }}
        div[data-baseweb="popover"] ul {{ background: var(--bg-alt)!important; }}
        div[data-baseweb="popover"] li {{ color: var(--text)!important; }}
        div[data-baseweb="popover"] li:hover {{ background: rgba(31,119,180,0.12)!important; }}
        div[data-baseweb="popover"] * {{ color: var(--text)!important; }}
        /* Placeholder text */
        div[data-baseweb="select"] span[data-baseweb="typo-labelsmall"] {{ color: var(--text)!important; opacity:.85; }}
        /* Date input specific (calendar popover) */
        .stDateInput input {{ background: var(--bg-alt)!important; color: var(--text)!important; border:1px solid var(--border)!important; }}
        div[data-baseweb="datepicker"] {{ background: var(--bg-alt)!important; border:1px solid var(--border)!important; color: var(--text)!important; }}
        div[data-baseweb="calendar"] {{ background: var(--bg-alt)!important; color: var(--text)!important; }}
        div[data-baseweb="calendar"] button, div[data-baseweb="calendar"] span {{ color: var(--text)!important; }}
        div[data-baseweb="calendar"] td, div[data-baseweb="calendar"] th {{ color: var(--text)!important; }}
        div[data-baseweb="calendar"] td:hover {{ background: rgba(31,119,180,0.15)!important; }}
        div[data-baseweb="calendar"] td[aria-selected="true"] {{ background: #ff3344 !important; color:#fff !important; }}
        ::-webkit-scrollbar {{ width:10px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius:6px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}
        {('''
        /* EXTRA LIGHT THEME DATEPICKER FIXES */
        /* Force any dark inline-styled sections to light background */
        div[data-baseweb="datepicker"] *[style*="#0E1117"],
        div[data-baseweb="datepicker"] *[style*="#0e1117"],
        div[data-baseweb="datepicker"] *[style*="rgb(14, 17, 23)"],
        div[data-baseweb="datepicker"] *[style*="#1E222A"],
        div[data-baseweb="datepicker"] *[style*="#1e222a"],
        div[data-baseweb="datepicker"] *[style*="rgb(30, 34, 42)"],
        div[data-baseweb="calendar"] *[style*="#0E1117"],
        div[data-baseweb="calendar"] *[style*="rgb(14, 17, 23)"],
        div[data-baseweb="calendar"] *[style*="#1E222A"],
        div[data-baseweb="calendar"] *[style*="rgb(30, 34, 42)"] {
            background: var(--bg-alt)!important; color: var(--text)!important;
        }
        /* Catch any remaining inline background declarations */
        div[data-baseweb="datepicker"] *[style*="background:#0E1117"],
        div[data-baseweb="datepicker"] *[style*="background: #0E1117"],
        div[data-baseweb="datepicker"] *[style*="background-color:#0E1117"],
        div[data-baseweb="datepicker"] *[style*="background-color: #0E1117"],
        div[data-baseweb="datepicker"] *[style*="background:rgb(14, 17, 23)"],
        div[data-baseweb="datepicker"] *[style*="background-color:rgb(14, 17, 23)"] {
            background: var(--bg-alt)!important; color: var(--text)!important;
        }
        /* Remove dark bar placeholder inside calendar (cell wrapper divs) */
        div[data-baseweb="calendar"] td > div { background: transparent!important; }
        /* Ensure visible selected day styles preserved */
        div[data-baseweb="calendar"] td[aria-selected="true"] { background:#ff3344!important; color:#fff!important; }
        /* Generic fallback: every nested div goes light (selection cell override kept above) */
        div[data-baseweb="datepicker"] div,
        div[data-baseweb="calendar"] div { background: var(--bg-alt)!important; }
        /* Header & quick-select panel */
        div[data-baseweb="calendar"] > div { background: var(--bg-alt)!important; }
        div[data-baseweb="calendar"] table { background: var(--bg-alt)!important; }
        div[data-baseweb="calendar"] div[role="row"] > div { background: var(--bg-alt)!important; }
        ''') if light else ''}
        </style>
        """
        st.markdown(style_block, unsafe_allow_html=True)

    def setup_page_config(self):
        st.set_page_config(
            page_title=DASHBOARD_CONFIG["title"],
            page_icon=DASHBOARD_CONFIG["page_icon"],
            layout=DASHBOARD_CONFIG["layout"],
            initial_sidebar_state=DASHBOARD_CONFIG["initial_sidebar_state"]
        )
        st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            color: #1f77b4;
            margin-bottom: 2rem;
        }
        button[title="Deploy your app"], a[kind="deployButton"], div[data-testid="stToolbarActions"] button[title="Deploy your app"] {display:none !important;}
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .sidebar-header {
            font-size: 1.5rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 1rem;
        }
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        @media (max-width: 1200px) {
            .main-header { font-size: 2.4rem; }
        }
        @media (max-width: 992px) {
            .main-header { font-size: 2rem; }
            .metric-card { margin-bottom: .75rem; }
        }
        @media (max-width: 768px) {
            .main-header { font-size: 1.75rem; }
            .stTabs [role="tablist"] { flex-wrap: wrap; }
            .stTabs [role="tab"] { flex: 1 1 45%; margin: 2px 0; }
        }
        @media (max-width: 576px) {
            .main-header { font-size: 1.55rem; }
            .metric-card { padding: .75rem; }
            .chart-container { padding: .75rem; }
            .stMetric { text-align: center; }
        }
        </style>
        """, unsafe_allow_html=True)
    
    def initialize_components(self):
        try:
            self.extractor = VahanDataExtractor()
            self.processor = DataProcessor()
            self.analyzer = GrowthAnalyzer()
            self.visualizer = VehicleDataVisualizer()
        except Exception as e:
            st.error(f"Error initializing components: {e}")
            st.stop()
    
    def render_sidebar(self):
        st.sidebar.markdown('<p class="sidebar-header">🎛️ Dashboard Controls</p>', unsafe_allow_html=True)
        new_theme = st.sidebar.radio("Theme", ["Light", "Dark"], horizontal=True, index=["Light","Dark"].index(st.session_state['ui_theme']))
        if new_theme != st.session_state['ui_theme']:
            st.session_state['ui_theme'] = new_theme
            self.apply_theme(new_theme)
            st.rerun()
        st.sidebar.subheader("📅 Date Range")
        default_end = date.today()
        default_start = default_end - timedelta(days=90)
        date_range = st.sidebar.date_input(
            "Select date range:",
            value=(default_start, default_end),
            min_value=date(2020, 1, 1),
            max_value=date.today()
        )
        st.sidebar.subheader("🚗 Vehicle Categories")
        selected_categories = st.sidebar.multiselect(
            "Select categories:",
            options=list(VEHICLE_CATEGORIES.keys()),
            default=list(VEHICLE_CATEGORIES.keys())
        )
        st.sidebar.subheader("📊 Analysis Type")
        analysis_type = st.sidebar.selectbox(
            "Choose analysis:",
            ["Overview", "State-wise Analysis", "Manufacturer Analysis", "Growth Trends", "Investment Insights"]
        )
        if analysis_type == "Manufacturer Analysis":
            st.sidebar.subheader("🏭 Manufacturers")
            available_manufacturers = []
            for cat in selected_categories:
                if cat in MAJOR_MANUFACTURERS:
                    available_manufacturers.extend(MAJOR_MANUFACTURERS[cat])
            selected_manufacturers = st.sidebar.multiselect(
                "Select manufacturers:",
                options=list(set(available_manufacturers)),
                default=list(set(available_manufacturers))[:5]
            )
        else:
            selected_manufacturers = []
        st.sidebar.subheader("🗺️ States")
        all_states = ["Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat", "Uttar Pradesh"]
        selected_states = st.sidebar.multiselect(
            "Select states:",
            options=all_states,
            default=all_states
        )
        st.sidebar.subheader("⏱️ Time Granularity")
        granularity = st.sidebar.radio(
            "Aggregate by:",
            ["Daily", "Monthly", "Quarterly"],
            horizontal=True
        )
        st.sidebar.subheader("🔄 Data Management")
        if st.sidebar.button("Refresh Data", type="primary"):
            self.refresh_data(date_range)
        st.sidebar.subheader("📥 Export Data")
        export_choices = ["CSV", "Excel"] + (["PDF"] if PDF_AVAILABLE else [])
        export_format = st.sidebar.selectbox(
            "Export format:",
            export_choices,
            index=0
        )
        if not PDF_AVAILABLE:
            st.sidebar.caption("PDF disabled (install fpdf2 to enable)")
        if st.sidebar.button("Export Data"):
            st.session_state["_trigger_export"] = True
        return {
            'date_range': date_range,
            'categories': selected_categories,
            'analysis_type': analysis_type,
            'manufacturers': selected_manufacturers,
            'export_format': export_format,
            'states': selected_states,
            'granularity': granularity
        }
    
    def render_header(self):
        st.markdown('<h1 class="main-header">📊 Vehicle Registration Investor Dashboard</h1>', unsafe_allow_html=True)
        cols = st.columns(4)
        metrics = [
            ("Total Registrations", "2.4M", "+12.5%"),
            ("Active Categories", "3", None),
            ("Manufacturers", "15+", "+2 new"),
            ("YoY Growth", "18.3%", "+2.1%")
        ]
        for col, (label, value, delta) in zip(cols, metrics):
            with col:
                st.metric(label=label, value=value, delta=delta)
    
    def load_sample_data(self, date_range, categories, states):
        start_date, end_date = date_range
        cache_fname = _cache_key("sample", start_date, end_date, sorted(categories), sorted(states)) + ".parquet"
        cache_path = self.file_cache_dir / cache_fname
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception:
                cache_path.unlink(missing_ok=True)
        df = load_or_generate_sample(start_date, end_date, categories, states)
        try:
            df.to_parquet(cache_path, index=False)
        except Exception:
            pass
        return df
    
    def _generate_sample_dataframe(self, start_date: date, end_date: date, categories: List[str], states: List[str]) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        sample_data = []
        for dt in dates:
            for state in states:
                for category in categories:
                    if category in MAJOR_MANUFACTURERS:
                        for manufacturer in MAJOR_MANUFACTURERS[category][:3]:
                            registrations = np.random.randint(50, 500)
                            sample_data.append({
                                'date': dt,
                                'state': state,
                                'vehicle_category': category,
                                'manufacturer': manufacturer,
                                'registrations': registrations,
                                'yoy_growth': np.random.normal(15, 10),
                                'qoq_growth': np.random.normal(5, 8),
                                'market_share': np.random.uniform(5, 25)
                            })
        return pd.DataFrame(sample_data)
    
    def render_overview(self, data, filters):
        st.header("📊 Registration Overview")
        col1, col2 = st.columns(2)
        with col1:
            trends_chart = self.visualizer.create_registration_trends_chart(
                data, "Daily Registration Trends"
            )
            st.plotly_chart(trends_chart, use_container_width=True)
        with col2:
            market_share_chart = self.visualizer.create_market_share_pie_chart(data)
            st.plotly_chart(market_share_chart, use_container_width=True)
        st.subheader("🌡️ Registration Heatmap")
        heatmap_chart = self.visualizer.create_heatmap(data)
        st.plotly_chart(heatmap_chart, use_container_width=True)
        st.subheader("📋 Summary Statistics")
        summary_data = data.groupby('vehicle_category').agg({
            'registrations': ['sum', 'mean', 'std'],
            'yoy_growth': 'mean',
            'market_share': 'mean'
        }).round(2)
        summary_data.columns = ['Total Registrations', 'Avg Daily', 'Std Dev', 'Avg YoY Growth (%)', 'Market Share (%)']
        st.dataframe(summary_data, use_container_width=True)
    
    def render_growth_analysis(self, data, filters):
        st.header("📈 Growth Analysis")
        col1, col2 = st.columns([1, 3])
        with col1:
            growth_metric = st.selectbox(
                "Select Growth Metric:",
                ["yoy_growth", "qoq_growth", "mom_growth"],
                format_func=lambda x: x.replace('_', ' ').title()
            )
        with col2:
            if growth_metric in data.columns:
                growth_chart = self.visualizer.create_growth_metrics_chart(data, growth_metric)
                st.plotly_chart(growth_chart, use_container_width=True)
        st.subheader("🏆 Growth Leaders & Laggards")
        if growth_metric in data.columns:
            latest_data = data[data['date'] == data['date'].max()].dropna(subset=[growth_metric])
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🚀 Top Performers")
                top_performers = latest_data.nlargest(5, growth_metric)[['manufacturer', 'vehicle_category', growth_metric]]
                st.dataframe(top_performers, use_container_width=True)
            with col2:
                st.markdown("### 📉 Bottom Performers")
                bottom_performers = latest_data.nsmallest(5, growth_metric)[['manufacturer', 'vehicle_category', growth_metric]]
                st.dataframe(bottom_performers, use_container_width=True)
    
    def render_manufacturer_analysis(self, data, filters):
        st.header("🏭 Manufacturer Analysis")
        if not filters['manufacturers']:
            st.warning("Please select manufacturers from the sidebar to view analysis.")
            return
        manufacturer_data = data[data['manufacturer'].isin(filters['manufacturers'])]
        comparison_chart = self.visualizer.create_comparison_chart(
            manufacturer_data, filters['manufacturers'], 'manufacturer'
        )
        st.plotly_chart(comparison_chart, use_container_width=True)
        st.subheader("📊 Manufacturer Performance Summary")
        perf_summary = manufacturer_data.groupby(['manufacturer', 'vehicle_category']).agg({
            'registrations': 'sum',
            'yoy_growth': 'mean',
            'qoq_growth': 'mean',
            'market_share': 'mean'
        }).round(2)
        st.dataframe(perf_summary, use_container_width=True)
    
    def render_investment_insights(self, data, filters):
        st.header("💰 Investment Insights")
        if 'investment_signal' in data.columns:
            st.subheader("🎯 Investment Signals")
            signal_summary = data.groupby(['investment_signal', 'vehicle_category']).size().unstack(fill_value=0)
            st.dataframe(signal_summary, use_container_width=True)
            signal_chart = self.visualizer.create_growth_metrics_chart(
                data.groupby('investment_signal').size().reset_index().rename(columns={0: 'Count'}),
                'Count'
            )
            st.plotly_chart(signal_chart, use_container_width=True)
        st.subheader("⚠️ Risk Assessment")
        volatility_data = data.groupby('vehicle_category')['registrations'].agg(['std', 'mean']).reset_index()
        volatility_data['cv'] = volatility_data['std'] / volatility_data['mean']
        volatility_data['risk_level'] = pd.cut(volatility_data['cv'], 
                                             bins=[0, 0.2, 0.4, float('inf')], 
                                             labels=['Low', 'Medium', 'High'])
        st.dataframe(volatility_data[['vehicle_category', 'cv', 'risk_level']], use_container_width=True)
        st.subheader("💡 Investment Recommendations")
        recommendations = [
            "🚀 **Strong Buy**: 2W segment showing consistent 20%+ YoY growth",
            "📈 **Buy**: 4W market recovering with improving QoQ numbers",
            "⚖️ **Hold**: 3W segment stable but limited growth potential",
            "🔍 **Watch**: Monitor EV adoption impact on traditional segments",
            "⚠️ **Risk Alert**: High volatility in luxury vehicle segment"
        ]
        for rec in recommendations:
            st.markdown(f"- {rec}")
    
    def refresh_data(self, date_range):
        try:
            for fp in self.file_cache_dir.glob("sample_*.parquet"):
                fp.unlink()
        except Exception:
            pass
        load_or_generate_sample.clear()
        with st.spinner("Refreshing data..."):
            st.success("Cache cleared. Fresh data will be generated on next load.")
            st.rerun()
    
    def export_data(self, df: pd.DataFrame, fmt: str):
        try:
            base_name = f"vehicle_registrations_{fmt.lower()}"
            payload = build_export_payload(df, fmt, base_name)
            return payload
        except RuntimeError as pdf_err:
            st.error(str(pdf_err))
            return None
        except Exception as e:
            st.error(f"Export failed: {e}")
            return None
    
    def aggregate_data(self, df: pd.DataFrame, granularity: str) -> pd.DataFrame:
        if granularity == "Daily" or df.empty:
            return df
        group_cols = ['state', 'vehicle_category', 'manufacturer']
        if granularity == "Monthly":
            agg_df = self.processor.aggregate_daily_to_monthly(df, group_cols)
        elif granularity == "Quarterly":
            agg_df = self.processor.aggregate_daily_to_quarterly(df, group_cols)
        else:
            return df
        try:
            yoy = self.analyzer.calculate_yoy_growth(agg_df, group_cols=group_cols)
            qoq = self.analyzer.calculate_qoq_growth(agg_df, group_cols=group_cols)
            for gdf in [(yoy, 'yoy_growth'), (qoq, 'qoq_growth')]:
                g, metric = gdf
                if metric in g.columns:
                    cols = ['date'] + group_cols + [metric]
                    agg_df = agg_df.merge(g[cols], on=['date'] + group_cols, how='left')
        except Exception as e:
            st.warning(f"Growth recomputation failed: {e}")
        return agg_df
    
    def run(self):
        try:
            filters = self.render_sidebar()
            self.render_header()
            data = self.load_sample_data(filters['date_range'], filters['categories'], filters['states'])
            data = self.aggregate_data(data, filters['granularity'])
            if st.session_state.get("_trigger_export"):
                payload = self.export_data(data, filters['export_format'])
                if payload:
                    st.download_button(
                        label=f"Download {filters['export_format'].upper()}",
                        data=payload['data'],
                        file_name=payload['filename'],
                        mime=payload['mime'],
                        type='primary'
                    )
                    st.success("Export ready.")
                st.session_state["_trigger_export"] = False
            if filters['analysis_type'] == "Overview":
                self.render_overview(data, filters)
            elif filters['analysis_type'] == "Growth Trends":
                self.render_growth_analysis(data, filters)
            elif filters['analysis_type'] == "Manufacturer Analysis":
                self.render_manufacturer_analysis(data, filters)
            elif filters['analysis_type'] == "Investment Insights":
                self.render_investment_insights(data, filters)
            else:
                st.info(f"{filters['analysis_type']} coming soon!")
            st.markdown("---")
            st.markdown("*Dashboard powered by Streamlit & Plotly | Data source: Vahan Dashboard*")
        except Exception as e:
            st.error(f"Dashboard error: {e}")
            st.error("Please check your configuration and try again.")

def main():
    try:
        dashboard = VehicleDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"Failed to initialize dashboard: {e}")
        st.error("Please ensure all dependencies are installed.")

if __name__ == "__main__":
    main()
