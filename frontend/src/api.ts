const BASE_URL = "http://localhost:8000"; // change later for production

// upload a single paper to the backend
export async function uploadPaper(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let message = `Failed to upload ${file.name}.`;
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {
    }
    throw new Error(message);
  }

  return res.json();
}

// ask a question about uploaded paper
export async function askQuestion(question: string) {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    let message = "Failed to get answer from backend.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  const data = await res.json();
  return data.answer;
}
