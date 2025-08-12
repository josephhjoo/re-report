export async function analyzeData(formData) {
    const res = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });
  
    if (!res.ok) {
      throw new Error(`Server error: ${res.status}`);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    return url;
  }
  
