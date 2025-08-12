from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from utils import (
    process_csv_and_get_metrics,
    call_gpt_summary,
    build_pdf,
    generate_charts,
    current_week_label,
    safe_filename
)

app = Flask(__name__)
CORS(app)

# Folder for temporary generated files
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        report_title = request.form.get("reportTitle", "Data Analysis Report")
        csv_file = request.files.get("file")
        if not csv_file:
            return jsonify({"error": "No CSV file uploaded"}), 400

        metrics, df = process_csv_and_get_metrics(csv_file)
        summary_text = call_gpt_summary(metrics)
        charts = generate_charts(df, OUTPUT_DIR)

        week_label = current_week_label()

        safe_title = safe_filename(report_title)
        pdf_path = os.path.join(OUTPUT_DIR, f"{safe_title}_{week_label}.pdf")

        build_pdf(report_title, week_label, metrics, charts, summary_text, pdf_path)

        return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
