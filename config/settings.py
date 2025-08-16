import os
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
CACHE_DIR = DATA_DIR / "cache"

for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXPORTS_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

VAHAN_CONFIG = {
    "base_url": "https://vahan.parivahan.gov.in/vahan4dashboard/",
    "login_url": "https://vahan.parivahan.gov.in/vahan4dashboard/",
    "endpoints": {
        "state_wise": "vahan/vahan/view/reportview.xhtml",
        "category_wise": "vahan/vahan/view/reportview.xhtml",
        "manufacturer_wise": "vahan/vahan/view/reportview.xhtml"
    },
    "request_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    },
    "rate_limit_delay": 2.0,
    "selenium": {
        "headless": True,
        "implicit_wait": 5,
        "explicit_wait": 20,
        "page_load_timeout": 60,
        "retry_attempts": 3,
        "retry_backoff_seconds": 5
    },
    "credentials": {
        "username_env": "VAHAN_USERNAME",
        "password_env": "VAHAN_PASSWORD"
    },
    "feature_flags": {
        "use_live_extraction_env": "USE_LIVE_VAHAN",
        "archive_raw_html": True
    }
}

VEHICLE_CATEGORIES = {
    "2W": {"name": "Two Wheeler", "subcategories": ["Motorcycle", "Scooter", "Moped"], "color": "#FF6B6B"},
    "3W": {"name": "Three Wheeler", "subcategories": ["Auto Rickshaw", "Commercial 3W"], "color": "#4ECDC4"},
    "4W": {"name": "Four Wheeler", "subcategories": ["Car", "SUV", "Commercial Vehicle"], "color": "#45B7D1"}
}

MAJOR_MANUFACTURERS = {
    "2W": ["Hero MotoCorp", "Honda", "TVS", "Bajaj", "Yamaha", "Royal Enfield"],
    "3W": ["Bajaj", "TVS", "Mahindra", "Piaggio", "Force Motors"],
    "4W": ["Maruti Suzuki", "Hyundai", "Tata Motors", "Mahindra", "Kia", "Honda", "Toyota"]
}

DASHBOARD_CONFIG = {
    "title": "Vehicle Registration Investor Dashboard",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "theme": {
        "primary_color": "#1f77b4",
        "background_color": "#ffffff",
        "secondary_background_color": "#f0f2f6",
        "text_color": "#262730"
    }
}

DATA_CONFIG = {
    "date_format": "%Y-%m-%d",
    "default_start_date": "2020-01-01",
    "cache_duration": 3600,
    "batch_size": 1000,
    "max_retries": 3
}

ANALYTICS_CONFIG = {
    "growth_metrics": ["YoY", "QoQ", "MoM"],
    "statistical_significance": 0.05,
    "outlier_threshold": 3.0,
    "smoothing_window": 7
}

EXPORT_CONFIG = {
    "formats": ["csv", "xlsx", "pdf"],
    "max_file_size": 50,
    "compression": True
}

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
    "rotation": "10 MB",
    "retention": "30 days"
}
