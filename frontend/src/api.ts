const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export interface PaperMetadata {
  pdf_id: string;
  filename: string;
  title: string | null;
  abstract: string | null;
  authors: string[] | null;
  domain: string | null;
  upload_date: string;
  chunk_count: number;
}

export interface SavedCluster {
  cluster_id: string;
  name: string;
  pdf_ids: string[];
  topics: string[];
  method: string;
  created_at: string;
}

export interface ClusteringSession {
  session_id: string;
  name: string;
  method: string;
  clusters: SavedCluster[];
  total_papers: number;
  outliers: string[];
  created_at: string;
}

export interface UploadResponse {
  status: string;
  filename: string;
  pdf_id: string;
  session_id: string;
}

// upload a single paper to the backend
export async function uploadPaper(file: File, sessionId?: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

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

// clean up session papers when user leaves
export function cleanupSession(sessionId: string): void {
  // Use sendBeacon for reliable delivery on page unload
  // Must use Blob with correct content-type for FastAPI to parse JSON
  const blob = new Blob(
    [JSON.stringify({ session_id: sessionId })],
    { type: 'application/json' }
  );
  navigator.sendBeacon(`${BASE_URL}/session/cleanup`, blob);
}

// Alternative cleanup using fetch (for manual cleanup)
export async function cleanupSessionAsync(sessionId: string): Promise<{
  status: string;
  papers_deleted: number;
  pdf_ids: string[];
}> {
  const res = await fetch(`${BASE_URL}/session/cleanup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!res.ok) {
    throw new Error("Failed to cleanup session.");
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

// get metadata for all papers
export async function getPapersMetadata(): Promise<PaperMetadata[]> {
  const res = await fetch(`${BASE_URL}/papers/metadata`);

  if (!res.ok) {
    throw new Error("Failed to fetch paper metadata.");
  }

  return res.json();
}

// save a clustering result
export async function saveClusteringResult(
  name: string,
  method: string,
  clusters: ClusterResult[],
  totalPapers: number,
  outliers?: string[]
): Promise<ClusteringSession> {
  const res = await fetch(`${BASE_URL}/clusters/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      method,
      clusters: clusters.map((c) => ({
        papers: c.papers,
        topics: c.topics,
      })),
      total_papers: totalPapers,
      outliers,
    }),
  });

  if (!res.ok) {
    let message = "Failed to save clustering result.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// get all saved clustering sessions
export async function getSavedSessions(): Promise<ClusteringSession[]> {
  const res = await fetch(`${BASE_URL}/clusters/sessions`);

  if (!res.ok) {
    throw new Error("Failed to fetch saved sessions.");
  }

  return res.json();
}

// get a specific saved session
export async function getSavedSession(sessionId: string): Promise<ClusteringSession> {
  const res = await fetch(`${BASE_URL}/clusters/sessions/${sessionId}`);

  if (!res.ok) {
    throw new Error("Failed to fetch session.");
  }

  return res.json();
}

// rename a clustering session
export async function renameSession(sessionId: string, newName: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/clusters/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_name: newName }),
  });

  if (!res.ok) {
    throw new Error("Failed to rename session.");
  }
}

// rename a cluster within a session
export async function renameCluster(
  sessionId: string,
  clusterId: string,
  newName: string
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/clusters/sessions/${sessionId}/clusters/${clusterId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_name: newName }),
    }
  );

  if (!res.ok) {
    throw new Error("Failed to rename cluster.");
  }
}

// delete a saved session
export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/clusters/sessions/${sessionId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error("Failed to delete session.");
  }
}

export interface ReferenceItem {
  index: number;
  pdf_id: string;
  formatted: string;
}

export interface LiteratureReviewResult {
  title: string;
  introduction: string;
  methodology_overview: string;
  key_findings: string;
  research_gaps: string;
  conclusion: string;
  references: ReferenceItem[];
  papers_analyzed: string[];
  citation_style: string;
  created_at: string;
}

// generate a literature review from selected papers
export async function generateLiteratureReview(
  pdfIds: string[],
  topic?: string,
  citationStyle: string = "apa"
): Promise<LiteratureReviewResult> {
  const res = await fetch(`${BASE_URL}/literature-review/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pdf_ids: pdfIds,
      topic: topic,
      citation_style: citationStyle,
    }),
  });

  if (!res.ok) {
    let message = "Failed to generate literature review.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.json();
}

// export literature review in specified format
export async function exportLiteratureReview(
  format: 'markdown' | 'latex' | 'docx',
  reviewData: LiteratureReviewResult
): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/literature-review/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      format: format,
      review: reviewData,
    }),
  });

  if (!res.ok) {
    let message = "Failed to export literature review.";
    try {
      const data = await res.json();
      if (data?.detail) message = data.detail;
    } catch {}
    throw new Error(message);
  }

  return res.blob();
}
