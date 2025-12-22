const BASE_URL = "http://localhost:8000"; // change later for production

// Types for literature review
export interface ClusterResult {
  id: number;
  papers: string[];
  size: number;
  topics: string[];
  summary: string | null;
}

export interface ClusterResponse {
  method: string;
  total_papers: number;
  num_clusters: number;
  clusters: ClusterResult[];
  outliers?: string[];
}

export interface SimilarPaper {
  pdf_id: string;
  similarity_score: number;
}

export interface SimilarPapersResponse {
  query_paper: string;
  similar_papers: SimilarPaper[];
}

export interface CompareResponse {
  pdf_ids: string[];
  similarities: string[];
  differences: string[];
  key_themes: string[];
  methodology_comparison: string | null;
}

export interface SynthesisCitation {
  id: number;
  document: string;
  section: string;
  text: string;
}

export interface SynthesizeResponse {
  synthesis: string;
  citations: SynthesisCitation[];
  methodology_comparison: string | null;
  findings_comparison: string | null;
  papers_analyzed: string[];
  confidence: string;
}

export interface PaperInfo {
  filename: string;
  pdf_id: string;
  path: string;
}

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

// clear all papers and vectors from the backend
export async function clearPapers() {
  const res = await fetch(`${BASE_URL}/clear`, {
    method: "POST",
  });

  if (!res.ok) {
    let message = "Failed to clear papers.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// get list of all uploaded papers
export async function getPapers(): Promise<PaperInfo[]> {
  const res = await fetch(`${BASE_URL}/papers`);

  if (!res.ok) {
    throw new Error("Failed to fetch papers.");
  }

  return res.json();
}

// cluster papers to find thematic groups
export async function clusterPapers(
  pdfIds?: string[],
  method: "kmeans" | "hierarchical" | "dbscan" = "hierarchical",
  params?: { n_clusters?: number; distance_threshold?: number; eps?: number; min_samples?: number }
): Promise<ClusterResponse> {
  const res = await fetch(`${BASE_URL}/literature-review/cluster`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pdf_ids: pdfIds,
      method,
      params,
    }),
  });

  if (!res.ok) {
    let message = "Clustering failed.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// find papers similar to a given paper
export async function findSimilarPapers(
  pdfId: string,
  topK: number = 5
): Promise<SimilarPapersResponse> {
  const res = await fetch(`${BASE_URL}/literature-review/similar/${pdfId}?top_k=${topK}`);

  if (!res.ok) {
    let message = "Failed to find similar papers.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// compare 2-5 papers
export async function comparePapers(pdfIds: string[]): Promise<CompareResponse> {
  const res = await fetch(`${BASE_URL}/literature-review/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdf_ids: pdfIds }),
  });

  if (!res.ok) {
    let message = "Comparison failed.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// synthesize findings across papers
export async function synthesizePapers(
  pdfIds: string[],
  focusQuestion?: string
): Promise<SynthesizeResponse> {
  const res = await fetch(`${BASE_URL}/literature-review/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pdf_ids: pdfIds,
      focus_question: focusQuestion,
    }),
  });

  if (!res.ok) {
    let message = "Synthesis failed.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}
