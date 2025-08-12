import React, { useState } from "react";

export default function ReportGenerator() {
  const [reportTitle, setReportTitle] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setPdfUrl(null);

    if (!file) {
      setError("Please upload a CSV file.");
      return;
    }
    if (!reportTitle.trim()) {
      setError("Please enter a report title.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("reportTitle", reportTitle.trim());

      const response = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        setError(err.error || "Failed to generate report.");
        setLoading(false);
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (e) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Custom Data Report Generator</h1>

      <form onSubmit={handleSubmit} style={styles.form}>
        <label style={styles.label}>
          Report Title
          <input
            type="text"
            value={reportTitle}
            onChange={(e) => setReportTitle(e.target.value)}
            placeholder="Enter your report title"
            style={styles.input}
            required
          />
        </label>

        <label style={styles.label}>
          Upload CSV File
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files[0])}
            style={styles.fileInput}
            required
          />
        </label>

        {error && <p style={styles.error}>{error}</p>}

        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? "Generating..." : "Generate PDF"}
        </button>
      </form>

      {pdfUrl && (
        <div style={styles.preview}>
          <h2>Generated Report Preview</h2>
          <iframe
            src={pdfUrl}
            title="Generated PDF Report"
            style={styles.iframe}
          />
          <a href={pdfUrl} download={`${reportTitle || "report"}.pdf`} style={styles.downloadLink}>
            Download PDF
          </a>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: 720,
    margin: "40px auto",
    fontFamily:
      "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    padding: 20,
    color: "#222",
  },
  title: {
    textAlign: "center",
    marginBottom: 32,
    fontWeight: "700",
    color: "#007ACC",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 20,
    backgroundColor: "#f9f9f9",
    padding: 24,
    borderRadius: 8,
    boxShadow:
      "0 2px 8px rgba(0,0,0,0.1)",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    fontWeight: "600",
    fontSize: 14,
    color: "#555",
  },
  input: {
    marginTop: 6,
    padding: "10px 12px",
    fontSize: 16,
    borderRadius: 4,
    border: "1.5px solid #ccc",
    outline: "none",
    transition: "border-color 0.2s ease",
  },
  fileInput: {
    marginTop: 6,
  },
  button: {
    marginTop: 10,
    padding: "14px 0",
    backgroundColor: "#007ACC",
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    transition: "background-color 0.3s ease",
  },
  error: {
    color: "#c00",
    fontWeight: "600",
  },
  preview: {
    marginTop: 40,
    textAlign: "center",
  },
  iframe: {
    width: "100%",
    height: 600,
    border: "1px solid #ccc",
    borderRadius: 6,
    boxShadow:
      "0 2px 12px rgba(0,0,0,0.1)",
  },
  downloadLink: {
    display: "inline-block",
    marginTop: 12,
    fontWeight: "600",
    color: "#007ACC",
    textDecoration: "none",
  },
};
