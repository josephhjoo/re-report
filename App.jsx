import React, { useState } from "react";
import { analyzeData } from "./api";

function App() {
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!name || !file) {
      setError("Please enter a name and upload a CSV file.");
      return;
    }

    const formData = new FormData();
    formData.append("agentName", name);
    formData.append("file", file);

    try {
      const url = await analyzeData(formData);
      setPdfUrl(url); // Display PDF in iframe
    } catch (err) {
      setError("Failed to generate PDF: " + err.message);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Report Generator</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Your name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit">Generate PDF</button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {pdfUrl && (
        <div style={{ marginTop: "20px" }}>
          <h2>Generated Report</h2>
          <iframe
            src={pdfUrl}
            width="100%"
            height="600px"
            title="Generated PDF"
          ></iframe>
        </div>
      )}
    </div>
  );
}

export default App;
