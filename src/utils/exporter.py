from __future__ import annotations
import pandas as pd
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    FPDF = object  # type: ignore


def export_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def export_to_excel(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
        summary = df.describe(include="all").transpose()
        summary.to_excel(writer, sheet_name="Summary")
    buffer.seek(0)
    return buffer.read()


class _PDF(FPDF):  # type: ignore
    def header(self):  # type: ignore
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Vehicle Registration Report", ln=True, align="C")
        self.ln(2)

    def footer(self):  # type: ignore
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 8, f"Page {self.page_no()}", 0, 0, "C")


def export_to_pdf(df: pd.DataFrame) -> bytes:
    if not PDF_AVAILABLE:
        raise RuntimeError("PDF export not available. Install dependency: pip install fpdf2")
    pdf = _PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary Statistics", ln=True)
    pdf.set_font("Helvetica", size=9)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if numeric_cols:
        summary = df[numeric_cols].describe().round(2)
        pdf.set_font("Courier", size=8)
        pdf.multi_cell(0, 5, summary.to_string())
    else:
        pdf.cell(0, 6, "No numeric columns for summary.", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Sample Rows", ln=True)
    pdf.set_font("Courier", size=7)
    preview = df.head(20).copy()
    for col in preview.columns:
        preview[col] = preview[col].astype(str).str.slice(0, 25)
    pdf.multi_cell(0, 4, preview.to_string(index=False))
    return bytes(pdf.output(dest="S"))


def build_export_payload(df: pd.DataFrame, fmt: str, base_name: str) -> Dict[str, Any]:
    fmt_lower = fmt.lower()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if fmt_lower in ("csv",):
        data = export_to_csv(df)
        mime = "text/csv"
        ext = "csv"
    elif fmt_lower in ("xlsx", "excel"):
        data = export_to_excel(df)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif fmt_lower in ("pdf",):
        data = export_to_pdf(df)
        mime = "application/pdf"
        ext = "pdf"
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    filename = f"{base_name}_{timestamp}.{ext}"
    return {"data": data, "mime": mime, "filename": filename}
