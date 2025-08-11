import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend suitable for scripts/servers
import matplotlib.pyplot as plt

from io import BytesIO
from fpdf import FPDF
from datetime import datetime

def process_csv_and_get_metrics(csv_file):
    """
    Reads CSV, returns metrics dict and the DataFrame itself.
    """
    df = pd.read_csv(csv_file)
    metrics = {
        "rows": len(df),
        "columns": list(df.columns),
        "preview":df.head(5).to_dict(orient="records")
    }
    return metrics, df

def call_gpt_structured(metrics):
    """
    Stub for GPT processing — replace with actual API call later.
    """
    return {
        "summary": f"Dataset contains {metrics['rows']} rows and {len(metrics['columns'])} columns.",
        "columns": metrics["columns"]
    }

def generate_charts(df, output_dir="output", prefix="chart"):
    """
    Generate charts based on columns detected in df.
    Returns list of dicts with 'title' and 'file' (path).
    """
    os.makedirs(output_dir, exist_ok=True)
    charts = []

    # Histogram for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    for col in numeric_cols:
        plt.figure(figsize=(6,4))
        df[col].dropna().hist(bins=20)
        plt.title(f'Histogram of {col}')
        plt.xlabel(col)
        plt.ylabel('Count')
        path = os.path.join(output_dir, f"{prefix}_{col}_hist.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        charts.append({"title": f"Histogram of {col}", "file": path})

    # Scatter plot: price vs sqft if both exist
    sqft_col = None
    if "price" in df.columns:
        for candidate in ["sqft", "sq. ft.", "square_feet"]:
            if candidate in df.columns:
                sqft_col = candidate
                break
        if sqft_col:
            plt.figure(figsize=(6,4))
            plt.scatter(df[sqft_col], df["price"], alpha=0.6)
            plt.title("Price vs. " + sqft_col)
            plt.xlabel(sqft_col)
            plt.ylabel("Price")
            path = os.path.join(output_dir, f"{prefix}_price_vs_sqft.png")
            plt.tight_layout()
            plt.savefig(path)
            plt.close()
            charts.append({"title": "Price vs. Square Footage", "file": path})

    # Boxplot price by bedrooms
    if "bedrooms" in df.columns and "price" in df.columns:
        plt.figure(figsize=(6,4))
        df_box = df[["bedrooms", "price"]].dropna()
        df_box.boxplot(column="price", by="bedrooms")
        plt.title("Price by Bedrooms")
        plt.suptitle("")  # remove default title
        plt.xlabel("Bedrooms")
        plt.ylabel("Price")
        path = os.path.join(output_dir, f"{prefix}_price_by_bedrooms.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        charts.append({"title": "Price by Bedrooms", "file": path})

    return charts

def build_pdf(agent_name, week_label, metrics, charts, gpt_json, output_path):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, f"Report for {agent_name}", ln=True, align="C")

    # Week label
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Week: {week_label}", ln=True)

    # Metrics summary
    pdf.cell(200, 10, f"Rows: {metrics.get('rows', 'N/A')}", ln=True)
    pdf.cell(200, 10, f"Columns: {', '.join(metrics.get('columns', []))}", ln=True)

    # GPT Summary
    pdf.multi_cell(0, 10, f"Summary:\n{gpt_json.get('summary', '')}")

    # Add charts
    for chart in charts:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, chart["title"], ln=True, align="C")
        # Add image (fit width 180, maintain aspect ratio)
        try:
            pdf.image(chart["file"], x=15, w=180)
        except Exception as e:
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Error loading image: {e}", ln=True)

    pdf.output(output_path)
    return output_path

# Optional helper to get current UTC week label
def current_week_label():
    return datetime.utcnow().strftime("%Y-%m-%d")
