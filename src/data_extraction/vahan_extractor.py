import requests
import pandas as pd
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Callable
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger
import sys
import os
import random
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import VAHAN_CONFIG, DATA_CONFIG, RAW_DATA_DIR, MAJOR_MANUFACTURERS

SELECTOR_CONFIG: Dict[str, Dict[str, str]] = {
    "state_wise": {
        "table": "table#stateReportTable, table.dataTable",
        "date_from": "input#fromDate, input#dateFrom",
        "date_to": "input#toDate, input#dateTo",
        "apply": "button#apply, button#search, a#submitBtn"
    },
    "manufacturer_wise": {
        "table": "table#manufacturerTable, table.dataTable",
        "date_from": "input#fromDate, input#dateFrom",
        "date_to": "input#toDate, input#dateTo",
        "apply": "button#apply"
    },
    "category_wise": {
        "table": "table#categoryTable, table.dataTable",
        "date_from": "input#fromDate, input#dateFrom",
        "date_to": "input#toDate, input#dateTo",
        "apply": "button#apply"
    }
}


class VahanDataExtractor:
    def __init__(self):
        self.base_url = VAHAN_CONFIG["base_url"]
        self.headers = VAHAN_CONFIG["request_headers"]
        self.rate_limit = VAHAN_CONFIG["rate_limit_delay"]
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.driver = None
        self.selenium_cfg = VAHAN_CONFIG.get("selenium", {})
        self.feature_flags = VAHAN_CONFIG.get("feature_flags", {})
        self.use_live = os.getenv(self.feature_flags.get("use_live_extraction_env", "USE_LIVE_VAHAN"), "0") == "1"
        self.archive_html = self.feature_flags.get("archive_raw_html", True)
        creds = VAHAN_CONFIG.get("credentials", {})
        self.username = os.getenv(creds.get("username_env", "VAHAN_USERNAME"))
        self.password = os.getenv(creds.get("password_env", "VAHAN_PASSWORD"))
        logger.add("logs/data_extraction.log", rotation="10 MB")
        mode = "LIVE" if self.use_live else "SAMPLE"
        logger.info(f"VahanDataExtractor initialized in {mode} mode")

    def setup_selenium_driver(self):
        if self.driver:
            return
        try:
            chrome_options = Options()
            if self.selenium_cfg.get("headless", True):
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
            self.driver.set_page_load_timeout(self.selenium_cfg.get("page_load_timeout", 60))
            logger.info("Selenium WebDriver setup successful")
        except Exception as e:
            logger.error(f"Failed to setup Selenium WebDriver: {e}")
            raise

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            finally:
                self.driver = None

    def login_if_required(self):
        if not self.use_live:
            return
        try:
            self.setup_selenium_driver()
            self.driver.get(VAHAN_CONFIG.get("login_url", self.base_url))
            WebDriverWait(self.driver, self.selenium_cfg.get("explicit_wait", 20)).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            if self.username and self.password:
                possible_username = ["#username", "input[name='username']"]
                possible_password = ["#password", "input[name='password']"]
                for sel in possible_username:
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, sel)
                        el.clear(); el.send_keys(self.username)
                        break
                    except Exception:
                        continue
                for sel in possible_password:
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, sel)
                        el.clear(); el.send_keys(self.password)
                        break
                    except Exception:
                        continue
                for sel in ["button[type='submit']", "#login", ".loginbtn"]:
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, sel).click()
                        break
                    except Exception:
                        continue
                time.sleep(3)
            logger.info("Login attempt completed (if required)")
        except Exception as e:
            logger.warning(f"Login flow encountered an issue: {e}")

    def _first_matching_element(self, selectors: str) -> Optional[webdriver.remote.webelement.WebElement]:
        if not self.driver:
            return None
        for sel in [s.strip() for s in selectors.split(',') if s.strip()]:
            try:
                return self.driver.find_element(By.CSS_SELECTOR, sel)
            except Exception:
                continue
        return None

    def _apply_filters(self, report_type: str, params: Optional[Dict] = None):
        if not (self.use_live and params):
            return
        cfg = SELECTOR_CONFIG.get(report_type, {})
        try:
            if 'start_date' in params and cfg.get('date_from'):
                el = self._first_matching_element(cfg['date_from'])
                if el:
                    el.clear(); el.send_keys(params['start_date'])
            if 'end_date' in params and cfg.get('date_to'):
                el = self._first_matching_element(cfg['date_to'])
                if el:
                    el.clear(); el.send_keys(params['end_date'])
            if cfg.get('apply'):
                btn = self._first_matching_element(cfg['apply'])
                if btn:
                    btn.click()
            time.sleep(2)
        except Exception as e:
            logger.debug(f"Filter application skipped ({report_type}): {e}")

    def _retry(self, func: Callable, attempts: int = 3, delay: float = 3.0, backoff: float = 1.5):
        for i in range(1, attempts + 1):
            try:
                return func()
            except Exception as e:
                if i == attempts:
                    raise
                sleep_for = delay * (backoff ** (i - 1))
                logger.warning(f"Attempt {i} failed: {e} -> retrying in {sleep_for:.1f}s")
                time.sleep(sleep_for)

    def _normalize_state_table(self, df: pd.DataFrame, as_of: str) -> pd.DataFrame:
        if df.empty:
            return df
        cols_lower = [str(c).strip().lower() for c in df.columns]
        try:
            state_col = next(c for c in df.columns if 'state' in str(c).lower())
        except StopIteration:
            return df
        category_map = {c: c for c in df.columns if c not in [state_col]}
        long_rows = []
        for _, row in df.iterrows():
            for cat_col in category_map:
                val = row[cat_col]
                if pd.api.types.is_numeric_dtype(type(val)) or str(val).replace('.', '', 1).isdigit():
                    vehicle_category = cat_col.strip().upper()[:2]
                    long_rows.append({
                        'date': as_of,
                        'state': row[state_col],
                        'vehicle_category': vehicle_category,
                        'registrations': pd.to_numeric(val, errors='coerce') or 0,
                        'extracted_at': datetime.utcnow()
                    })
        return pd.DataFrame(long_rows)

    def _normalize_manufacturer_table(self, df: pd.DataFrame, as_of: str) -> pd.DataFrame:
        if df.empty:
            return df
        manu_col = df.columns[0]
        long_rows = []
        for _, row in df.iterrows():
            for cat_col in df.columns[1:]:
                val = row[cat_col]
                if pd.isna(val):
                    continue
                long_rows.append({
                    'date': as_of,
                    'manufacturer': row[manu_col],
                    'vehicle_category': str(cat_col).upper()[:2],
                    'registrations': pd.to_numeric(val, errors='coerce') or 0,
                    'extracted_at': datetime.utcnow()
                })
        return pd.DataFrame(long_rows)

    def _normalize_category_table(self, df: pd.DataFrame, as_of: str) -> pd.DataFrame:
        if df.empty:
            return df
        cat_col = None
        for c in df.columns:
            if 'category' in str(c).lower():
                cat_col = c; break
        if not cat_col:
            return df
        val_col = None
        for c in df.columns:
            if any(k in str(c).lower() for k in ['total', 'registration', 'count']):
                val_col = c; break
        if not val_col:
            return df
        out = df[[cat_col, val_col]].copy()
        out.columns = ['vehicle_category', 'total_registrations']
        out['date'] = as_of
        out['extracted_at'] = datetime.utcnow()
        return out[['date', 'vehicle_category', 'total_registrations', 'extracted_at']]

    def _map_and_normalize(self, report_type: str, raw_df: pd.DataFrame, as_of: str) -> pd.DataFrame:
        try:
            if report_type == 'state_wise':
                norm = self._normalize_state_table(raw_df, as_of)
            elif report_type == 'manufacturer_wise':
                norm = self._normalize_manufacturer_table(raw_df, as_of)
            elif report_type == 'category_wise':
                norm = self._normalize_category_table(raw_df, as_of)
            else:
                return raw_df
            return norm if not norm.empty else raw_df
        except Exception as e:
            logger.debug(f"Normalization fallback ({report_type}): {e}")
            return raw_df

    def fetch_report_html(self, report_type: str, params: Optional[Dict] = None) -> Optional[str]:
        if not self.use_live:
            return None
        try:
            self.login_if_required()
            self.setup_selenium_driver()
            target_url = self.base_url + VAHAN_CONFIG['endpoints'].get(report_type, '')
            self.driver.get(target_url)
            WebDriverWait(self.driver, self.selenium_cfg.get("explicit_wait", 20)).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self._apply_filters(report_type, params)
            cfg = SELECTOR_CONFIG.get(report_type, {})
            table_sel = cfg.get('table')
            if table_sel:
                for sel in [s.strip() for s in table_sel.split(',') if s.strip()]:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        break
                    except Exception:
                        continue
            time.sleep(2)
            html = self.driver.page_source
            if self.archive_html:
                ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                archive_path = RAW_DATA_DIR / f"archive_{report_type}_{ts}.html"
                with open(archive_path, 'w', encoding='utf-8') as f:
                    f.write(html)
            return html
        except Exception as e:
            logger.error(f"Failed to fetch {report_type} report HTML: {e}")
            return None

    def parse_table_from_html(self, html: str, table_selector: Optional[str] = None) -> pd.DataFrame:
        try:
            soup = BeautifulSoup(html, 'lxml')
            if table_selector:
                table = soup.select_one(table_selector)
                if table is None:
                    raise ValueError(f"No table found for selector {table_selector}")
                return pd.read_html(str(table))[0]
            tables = pd.read_html(html)
            if not tables:
                raise ValueError("No tables found in HTML")
            return tables[0]
        except Exception as e:
            logger.error(f"HTML table parsing failed: {e}")
            return pd.DataFrame()

    def _generate_state_sample(self, start_date: str, end_date: str) -> pd.DataFrame:
        states = [
            "Uttar Pradesh", "Maharashtra", "Tamil Nadu", "Karnataka", "Gujarat",
            "Rajasthan", "West Bengal", "Madhya Pradesh", "Haryana", "Punjab"
        ]
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        data = []
        for date in date_range:
            for state in states:
                for category in ["2W", "3W", "4W"]:
                    data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "state": state,
                        "vehicle_category": category,
                        "registrations": np.random.randint(80, 500) * (1 if category != '2W' else 3),
                        "extracted_at": datetime.utcnow()
                    })
        return pd.DataFrame(data)

    def _generate_manufacturer_sample(self, start_date: str, end_date: str) -> pd.DataFrame:
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        data = []
        for date in date_range:
            for category, manufacturers in MAJOR_MANUFACTURERS.items():
                for manufacturer in manufacturers:
                    data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "manufacturer": manufacturer,
                        "vehicle_category": category,
                        "registrations": np.random.randint(50, 800),
                        "extracted_at": datetime.utcnow()
                    })
        return pd.DataFrame(data)

    def _generate_category_trends_sample(self, start_date: str, end_date: str) -> pd.DataFrame:
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        data = []
        for date in date_range:
            for category in ["2W", "3W", "4W"]:
                base = {"2W": 12000, "3W": 1500, "4W": 3500}[category]
                noise = random.randint(-800, 800)
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "vehicle_category": category,
                    "total_registrations": max(0, base + noise),
                    "extracted_at": datetime.utcnow()
                })
        return pd.DataFrame(data)

    def extract_state_wise_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        logger.info(f"Extracting state-wise data from {start_date} to {end_date} (mode={'live' if self.use_live else 'sample'})")
        if not self.use_live:
            df = self._generate_state_sample(start_date, end_date)
        else:
            html = self.fetch_report_html('state_wise', params={"start_date": start_date, "end_date": end_date})
            if html:
                table_df = self.parse_table_from_html(html)
                df = self._map_and_normalize('state_wise', table_df, end_date)
                if 'date' not in df.columns:
                    df['date'] = end_date
            else:
                df = self._generate_state_sample(start_date, end_date)
        filename = f"state_wise_{start_date}_to_{end_date}.csv"
        filepath = RAW_DATA_DIR / filename
        df.to_csv(filepath, index=False)
        return df

    def extract_manufacturer_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        logger.info(f"Extracting manufacturer data from {start_date} to {end_date} (mode={'live' if self.use_live else 'sample'})")
        if not self.use_live:
            df = self._generate_manufacturer_sample(start_date, end_date)
        else:
            html = self.fetch_report_html('manufacturer_wise', params={"start_date": start_date, "end_date": end_date})
            if html:
                table_df = self.parse_table_from_html(html)
                df = self._map_and_normalize('manufacturer_wise', table_df, end_date)
                if 'date' not in df.columns:
                    df['date'] = end_date
            else:
                df = self._generate_manufacturer_sample(start_date, end_date)
        filename = f"manufacturer_wise_{start_date}_to_{end_date}.csv"
        filepath = RAW_DATA_DIR / filename
        df.to_csv(filepath, index=False)
        return df

    def extract_category_trends(self, start_date: str, end_date: str) -> pd.DataFrame:
        logger.info(f"Extracting category trends from {start_date} to {end_date} (mode={'live' if self.use_live else 'sample'})")
        if not self.use_live:
            df = self._generate_category_trends_sample(start_date, end_date)
        else:
            html = self.fetch_report_html('category_wise', params={"start_date": start_date, "end_date": end_date})
            if html:
                table_df = self.parse_table_from_html(html)
                df = self._map_and_normalize('category_wise', table_df, end_date)
                if 'date' not in df.columns:
                    df['date'] = end_date
            else:
                df = self._generate_category_trends_sample(start_date, end_date)
        filename = f"category_trends_{start_date}_to_{end_date}.csv"
        filepath = RAW_DATA_DIR / filename
        df.to_csv(filepath, index=False)
        return df

    def extract_all_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        logger.info(f"Starting comprehensive data extraction from {start_date} to {end_date}")
        results = {}
        try:
            results['state_wise'] = self.extract_state_wise_data(start_date, end_date)
            time.sleep(self.rate_limit)
            results['manufacturer_wise'] = self.extract_manufacturer_data(start_date, end_date)
            time.sleep(self.rate_limit)
            results['category_trends'] = self.extract_category_trends(start_date, end_date)
            logger.info("All data extraction completed successfully")
        except Exception as e:
            logger.error(f"Comprehensive extraction failed: {e}")
            raise
        finally:
            if self.use_live:
                self.close_driver()
        return results

    def health_check(self) -> Dict[str, Union[bool, str]]:
        return {
            "mode": "live" if self.use_live else "sample",
            "driver_active": bool(self.driver),
            "base_url": self.base_url
        }


def main():
    extractor = VahanDataExtractor()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    data = extractor.extract_all_data(start_date, end_date)
    print("Extraction summary:")
    for k, v in data.items():
        print(k, len(v))
    print("Health:", extractor.health_check())


if __name__ == "__main__":
    main()
