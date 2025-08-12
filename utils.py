# backend/app/utils.py
import os
import json
import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # IMPORTANT: headless backend for servers
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from fpdf import FPDF
from datetime import datetime
from dateutil.parser import parse as parse_date  # tolerant date parsing
from openai import OpenAI

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Initialize OpenAI client (reads OPENAI_API_KEY from env)
client = OpenAI()

def clean_numeric(series):
    """Remove currency symbols, commas, %, and convert to float."""
    return pd.to_numeric(series.replace(r'[^\d.-]', '', regex=True), errors='coerce')

def detect_and_parse_dates(series):
    """Try parsing as dates safely."""
    try:
        return pd.to_datetime(series, errors="coerce", dayfirst=False)
    except Exception:
        return series

def ask_gpt_for_charts(df):
    """Ask GPT for chart suggestions based on the dataset."""
    sample_data = df.head(5).to_dict(orient="records")

    system_prompt = (
        "You are a data visualization assistant. "
        "Given dataset column names and sample values, suggest 3-5 charts that would give useful insights. "
        "Only return valid JSON — no text before or after."
    )

    user_prompt = {
        "columns": list(df.columns),
        "sample_rows": sample_data
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Dataset info:\n{json.dumps(user_prompt)}\n\n"
                    "Return a JSON array where each element is an object:\n"
                    "{'title': str, 'type': 'bar'|'line'|'scatter'|'hist', 'x': str, 'y': str or null}.\n"
                    "No explanation, only JSON."
                )
            }
        ]
    )

    return response.choices[0].message.content.strip()


def parse_chart_suggestions(gpt_text):
    """Parse GPT's JSON output safely."""
    try:
        charts = json.loads(gpt_text)
        if isinstance(charts, list):
            return charts
        else:
            print("[generate_charts] GPT output was not a list.")
            return []
    except json.JSONDecodeError as e:
        print("[generate_charts] GPT suggestion parsing failed:", e)
        return []

# -------------------------
# Data processing utilities
# -------------------------
def process_csv_and_get_metrics(csv_file):
    """
    Read CSV (file-like or path). Return (metrics_dict, dataframe).
    Metrics includes numeric_stats and top_categories for GPT context.
    """
    # Accept file-like object or path
    if hasattr(csv_file, "read"):
        df = pd.read_csv(csv_file)
    else:
        df = pd.read_csv(str(csv_file))

    # Basic metrics
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_stats = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        numeric_stats[col] = {
            "count": int(series.count()),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "min": float(series.min()),
            "max": float(series.max()),
            "std": float(series.std()) if series.count() > 1 else 0.0
        }

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    top_categories = {}
    for col in cat_cols:
        top = df[col].dropna().value_counts().head(5).to_dict()
        if top:
            top_categories[col] = top

    # Try to detect date columns
    possible_dates = []
    for col in df.columns:
        if df[col].dtype == "datetime64[ns]":
            possible_dates.append(col)
        elif df[col].dtype == "object":
            # try parsing small sample
            sample = df[col].dropna().head(20).astype(str)
            parsed = 0
            for s in sample:
                try:
                    _ = parse_date(s)
                    parsed += 1
                except Exception:
                    break
            if parsed >= max(1, len(sample)//2):
                possible_dates.append(col)

    metrics = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "numeric_stats": numeric_stats,
        "top_categories": top_categories,
        "date_columns": possible_dates,
        "preview": df.head(8).to_dict(orient="records")
    }
    return metrics, df

# -------------------------
# GPT-driven suggestions
# -------------------------
def _safe_json_load(text):
    """Try to parse JSON from GPT output robustly."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Try extracting JSON substring heuristically
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
    return None

def suggest_charts_with_gpt(df, max_suggestions=5, sample_size=20):
    """
    Ask GPT-4 to suggest up to max_suggestions charts for dataframe df.
    Returns a list of dicts:
    {title, type, x, y, agg}
    """
    # Sample some rows to keep prompt small
    sample = df.head(sample_size).to_dict(orient="records")
    columns = list(df.columns)

    system_prompt = (
        "You are a data visualization assistant. "
        "Given dataset columns and sample rows, suggest charts to understand the data. "
        f"Return JSON list of up to {max_suggestions} items with keys: "
        "\"title\", \"type\" (histogram, bar, line, scatter, box, pie, timeseries), "
        "\"x\" (column name or null), \"y\" (column name or null), and \"agg\" (mean, sum, count, or null). "
        "Return JSON only, no explanations."
    )

    user_prompt = json.dumps({
        "columns": columns,
        "sample_rows": sample,
        "notes": "Suggest histogram for numeric column, scatter for two numeric, bar for categorical vs numeric, timeseries for dates."
    }, default=str)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=700
        )
        content = response.choices[0].message.content
        parsed = _safe_json_load(content)
        if not parsed or not isinstance(parsed, list):
            return []
        # Normalize results
        suggestions = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            suggestions.append({
                "title": item.get("title", "Chart"),
                "type": item.get("type", "").lower(),
                "x": item.get("x"),
                "y": item.get("y"),
                "agg": item.get("agg")
            })
        return suggestions[:max_suggestions]
    except Exception as e:
        print(f"[suggest_charts_with_gpt] GPT error: {e}")
        return []

# -------------------------
# Chart generation
# -------------------------
def _is_numeric(series):
    return pd.api.types.is_numeric_dtype(series)

def _is_datetime(series):
    return pd.api.types.is_datetime64_any_dtype(series)

def _ensure_datetime(series):
    # attempt to coerce to datetime
    try:
        return pd.to_datetime(series, format="%d/%m/%Y %H:%M:%S", errors="coerce")
    except Exception:
        return series

def generate_charts(df, output_dir):
    """Generate charts dynamically from GPT suggestions."""
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Ask GPT for chart suggestions
    gpt_output = ask_gpt_for_charts(df)

    # Step 2: Parse GPT's JSON safely
    chart_suggestions = parse_chart_suggestions(gpt_output)

    generated_paths = []

    # Step 3: Generate each chart
    for chart in chart_suggestions:
        try:
            chart_type = chart.get("type")
            title = chart.get("title", "Untitled Chart")
            x_col = chart.get("x")
            y_col = chart.get("y")

            if x_col not in df.columns or (y_col and y_col not in df.columns):
                print(f"[generate_charts] Skipping invalid chart: {title}")
                continue

            plt.figure(figsize=(6, 4))
            if chart_type == "bar":
                df.groupby(x_col)[y_col].mean().plot(kind="bar")
            elif chart_type == "line":
                df.plot(x=x_col, y=y_col, kind="line")
            elif chart_type == "scatter":
                df.plot.scatter(x=x_col, y=y_col)
            elif chart_type == "hist":
                df[x_col].plot(kind="hist", bins=20)
            else:
                print(f"[generate_charts] Unknown chart type: {chart_type}")
                continue

            plt.title(title)
            plt.tight_layout()

            chart_path = os.path.join(output_dir, f"{title.replace(' ', '_')}.png")
            plt.savefig(chart_path)
            plt.close()

            generated_paths.append(chart_path)

        except Exception as e:
            print(f"[generate_charts] error creating chart '{chart.get('title', 'Untitled')}':", e)

    return generated_paths



def safe_filename(s):
    # basic filename sanitizer
    keep = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return "".join(c for c in s if c in keep).replace(" ", "_")[:100]

# -------------------------
# GPT summary (plain text)
# -------------------------
def call_gpt_summary(metrics):
    """
    Use GPT to generate a short plain-text summary of the dataset based on metrics dict.
    Returns a string (not JSON).
    """
    system = "You are a helpful data analyst. Produce a concise (3-6 sentence) executive summary for a professional audience."
    numeric = metrics.get("numeric_stats", {})
    tops = metrics.get("top_categories", {})
    preview = metrics.get("preview", [])

    user = (
        "Dataset summary:\n"
        f"- rows: {metrics.get('rows')}\n"
        f"- columns: {metrics.get('columns')}\n"
        f"- numeric_stats: {json.dumps(numeric, default=str)[:1500]}\n"
        f"- top_categories: {json.dumps(tops, default=str)[:1500]}\n"
        f"- preview rows: {json.dumps(preview, default=str)[:1500]}\n\n"
        "Write a concise executive summary (3-6 sentences) highlighting key patterns, "
        "notable distributions, and recommendations. Return plain text only."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.2,
            max_tokens=300
        )
        text = resp.choices[0].message.content.strip()
        return text
    except Exception as e:
        print(f"[call_gpt_summary] GPT error: {e}")
        return "Unable to generate summary."

# -------------------------
# PDF builder (embeds charts)
# -------------------------
def build_pdf(agent_name, week_label, metrics, charts, summary_text, output_path):
    """Build PDF with summary and charts."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    # Title
    title = f"Data Analysis Report - {agent_name} - {week_label}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))

    # Summary Section
    story.append(Paragraph("<b>AI Summary</b>", styles["Heading2"]))
    story.append(Paragraph(summary_text, styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Dataset Metrics Section
    story.append(Paragraph("<b>Dataset Overview</b>", styles["Heading2"]))
    story.append(Paragraph(f"Rows: {metrics['rows']}", styles["Normal"]))
    story.append(Paragraph(f"Columns: {metrics['columns']}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Charts Section
    if charts:
        story.append(Paragraph("<b>Visualizations</b>", styles["Heading2"]))
        for chart_path in charts:
            try:
                story.append(Image(chart_path, width=5.5 * inch, height=3.5 * inch))
                story.append(Spacer(1, 0.3 * inch))
            except Exception as e:
                print(f"[build_pdf] Could not add chart {chart_path}: {e}")

    doc.build(story)



# -------------------------
# small helpers
# -------------------------
import string
def split_long_text(text, width):
    """Naive splitter preserving paragraphs"""
    if not text:
        return []
    lines = []
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
            continue
        while len(para) > width:
            # break at last space before width
            idx = para.rfind(" ", 0, width)
            if idx <= 0:
                idx = width
            lines.append(para[:idx])
            para = para[idx:].lstrip()
        if para:
            lines.append(para)
    return lines

def current_week_label():
    return datetime.utcnow().strftime("%Y-%m-%d")
