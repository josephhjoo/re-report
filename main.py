from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from utils import (
    process_csv_and_get_metrics,
    call_gpt_summary,
    build_pdf,
    generate_charts,
    current_week_label
)

app = Flask(__name__)
CORS(app)

# Folder for temporary generated files
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        agent_name = request.form.get("agentName", "Unknown Agent")
        csv_file = request.files.get("file")
        if not csv_file:
            return jsonify({"error": "No CSV file uploaded"}), 400

        # Process CSV to get metrics and dataframe
        metrics, df = process_csv_and_get_metrics(csv_file)

        # Get AI-written summary
        summary_text = call_gpt_summary(metrics)

        # Generate AI-suggested charts
        charts = generate_charts(df, OUTPUT_DIR)

        # Create PDF
        week_label = current_week_label()
        pdf_path = os.path.join(OUTPUT_DIR, f"report_{agent_name}_{week_label}.pdf")
        build_pdf(agent_name, week_label, metrics, charts, summary_text, pdf_path)

        # Return PDF to frontend
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)

    except Exception as e:
        print(f"[analyze] Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
