import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone

from ingest_paper import ingest_paper
from query_improved import content_generator
from conversation import conversation_store, Conversation
from rate_limit import rate_limiter
from cache import embedding_cache
from batch_processor import batch_job_store, process_batch

from literature_review import (
    compare_papers,
    synthesize_findings,
    extract_methodology_summary,
)

from clustering import (
    find_similar_papers,
    analyze_paper_collection,
    get_all_pdf_ids,
)

from paper_store import paper_store
from cluster_store import cluster_store

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Initialize Pinecone client
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))


# ---------------- FastAPI app ----------------

app = FastAPI(
    title="ResearchQ Backend",
    description="Backend API for uploading research papers and asking questions.",
)

# ---------------- CORS ----------------
# Allow your Vite dev server on localhost:5173
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # during early dev you can use ["*"] if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Paths / storage ----------------

BASE_DIR = Path(__file__).resolve().parent
TEST_PAPERS_DIR = BASE_DIR / "test_papers"
TEST_PAPERS_DIR.mkdir(exist_ok=True)


# ---------------- Pydantic models ----------------

class AskRequest(BaseModel):
  question: str
  pdf_ids: list[str] = None
  conversation_id: str = None

class Citation(BaseModel):
    id: int
    document: str
    section: str
    text: str

class ErrorDetail(BaseModel):
  error_code: str
  message: str
  suggestion: Optional[str] = None

class AskResponse(BaseModel):
  answer: str
  citations: list[Citation] = []
  warning: Optional[str] = None
  confidence: Optional[str] = None
  error: Optional[ErrorDetail] = None
  conversation_id: Optional[str] = None

class UploadResponse(BaseModel):
  status: str
  filename: str

class PaperInfo(BaseModel):
  filename: str
  pdf_id: str
  path: str

class ClearResponse(BaseModel):
  status: str
  message: str

class DeletePaperRequest(BaseModel):
  pdf_id: str

class ConversationInfo(BaseModel):
  id: str
  message_count: int
  created_at: str
  last_active: str

class UploadRequest(BaseModel):
    domain: Optional[str] = None

class BatchUploadResponse(BaseModel):
    job_id: str
    status: str
    file_count: int
    message: str

class BatchJobResult(BaseModel):
    pdf_path: str
    pdf_id: str
    status: str
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class BatchJobStatus(BaseModel):
    job_id: str
    status: str
    progress: str
    pdf_paths: List[str]
    results: List[BatchJobResult]
    created_at: str
    completed_at: Optional[str] = None
    domain: Optional[str] = None

class FolderIngestRequest(BaseModel):
    folder_path: str
    domain: Optional[str] = None

class ClusterRequest(BaseModel):
    pdf_ids: Optional[List[str]] = None
    method: str = "hierarchical"
    params: Optional[Dict[str, Any]] = None

class ClusterResponse(BaseModel):
    method: str
    total_papers: int
    num_clusters: int
    clusters: List[Dict[str, Any]]
    outliers: Optional[List[str]] = None

class SimilarPaperResponse(BaseModel):
    pdf_id: str
    similarity_score: float

class CompareRequest(BaseModel):
    pdf_ids: List[str]  # 2-5 papers

class CompareResponse(BaseModel):
    pdf_ids: List[str]
    similarities: List[str]
    differences: List[str]
    key_themes: List[str]
    methodology_comparison: Optional[str] = None

class SynthesizeRequest(BaseModel):
    pdf_ids: List[str]
    focus_question: Optional[str] = None

class SynthesizeResponse(BaseModel):
    synthesis: str
    citations: List[Dict[str, Any]]
    methodology_comparison: Optional[str] = None
    findings_comparison: Optional[str] = None
    papers_analyzed: List[str]
    confidence: str

class PaperMetadataResponse(BaseModel):
    pdf_id: str
    filename: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    domain: Optional[str] = None
    upload_date: str
    chunk_count: int

class SaveClusterRequest(BaseModel):
    name: str
    method: str
    clusters: List[Dict[str, Any]]
    total_papers: int
    outliers: Optional[List[str]] = None

class RenameClusterRequest(BaseModel):
    new_name: str

class SavedClusterResponse(BaseModel):
    cluster_id: str
    name: str
    pdf_ids: List[str]
    topics: List[str]
    method: str
    created_at: str

class ClusteringSessionResponse(BaseModel):
    session_id: str
    name: str
    method: str
    clusters: List[SavedClusterResponse]
    total_papers: int
    outliers: List[str]
    created_at: str

class GenerateReviewRequest(BaseModel):
    pdf_ids: List[str]
    title: Optional[str] = None
    citation_style: str = "apa"

class LiteratureReviewResponse(BaseModel):
    title: str
    introduction: str
    methodology_overview: str
    key_findings: str
    research_gaps: str
    conclusion: str
    references: List[str]
    citation_style: str

# ---------------- Routes ----------------

@app.get("/")
async def root():
  return {"status": "ok", "message": "ResearchQ backend is running"}

# accepts a single PDF file and saves it to the backend/test_papers
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), domain: Optional[str] = None):
  if file.content_type not in ("application/pdf", "application/x-pdf"):
    raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

  safe_filename = file.filename.replace(" ", "_")
  dest_path = TEST_PAPERS_DIR / safe_filename

  try:
    file_bytes = await file.read()

    if len(file_bytes) > 50 * 1024 * 1024:
      raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
    
    if not file_bytes.startswith(b'%PDF'):
      raise HTTPException(status_code=400, detail="Invalid PDF file.")
    
    dest_path.write_bytes(file_bytes)

    pdf_id = safe_filename.replace(".pdf", "")
    result = ingest_paper(dest_path, pdf_id=pdf_id, clear_existing=False, domain=domain)

    # Store paper metadata
    chunk_count = result.get("chunks", 0) if isinstance(result, dict) else 0
    paper_store.add_paper(
        pdf_id=pdf_id,
        filename=safe_filename,
        domain=domain,
        chunk_count=chunk_count,
    )
  except HTTPException:
    raise
  except Exception as e:
    if dest_path.exists():
      dest_path.unlink()
    
    error_message = str(e)
    if "NoTextExtractedError" in error_message or "no text" in error_message.lower():
      raise HTTPException(
        status_code=422,
        detail="Could not extract text from this PDF. It may be scanned or image-only. Try a different file."
      )
    raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")

  return UploadResponse(status="success", filename=safe_filename)

# accepts JSON and uses RAG pipeline to answer
@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
  question = payload.question.strip()
  if not question:
    raise HTTPException(status_code=400, detail="Question cannot be empty.")

  try:
    conversation = conversation_store.get_or_create(
        conversation_id=payload.conversation_id,
        pdf_ids=payload.pdf_ids
    )
    
    history = conversation.get_history(max_turns=3)
    result = content_generator(question, pdf_ids=payload.pdf_ids, conversation_history=history)

    answer = result.get("answer", "")
    citations = result.get("citations", [])

    conversation.add_message("user", question)
    conversation.add_message("assistant", answer, citations)

    warning = result.get("warning") or result.get("hallucination_warning")
    confidence = result.get("confidence")

    error = None
    if "error_code" in result:
      error = ErrorDetail(
        error_code=result["error_code"],
        message=result.get("error", "Unknown error"),
        suggestion=get_error_suggestion(result["error_code"])
      )
    
    if not answer.strip():
      answer = "I was unable to generate an answer. Please try rephrasing your question"

    return AskResponse(
        answer=answer,
        citations=citations,
        warning=warning,
        confidence=confidence,
        error=error,
        conversation_id=conversation.id
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}")

# get user-friendly suggestion for error codes
def get_error_suggestion(error_code: str) -> str:
  suggestions = {
      "NO_DOCUMENTS": "Upload a PDF document first using the upload button.",
      "LOW_RELEVANCE": "Try rephrasing your question or upload documents more relevant to your topic.",
      "EMPTY_CHUNKS": "The documents may have parsing issues. Try re-uploading.",
      "RETRIEVAL_ERROR": "There was a problem searching. Please try again in a moment.",
      "GENERATION_ERROR": "There was a problem generating the answer. Please try again.",
      "GENERATION_FAILED": "The AI couldn't generate a response. Try a simpler question.",
  }
  return suggestions.get(error_code, "Please try again or contact support.")

# Clear all vectors from Pinecone and delete local PDF files
@app.post("/clear", response_model=ClearResponse)
async def clear_data():
  try:
    # Clear Pinecone vectors
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    index.delete(delete_all=True)

    # Delete local PDF files
    deleted_files = []
    for pdf_path in TEST_PAPERS_DIR.glob("*.pdf"):
      pdf_path.unlink()
      deleted_files.append(pdf_path.name)

    # Clear paper and cluster stores
    paper_store.clear()
    cluster_store.clear()

    return ClearResponse(
      status="success",
      message=f"Cleared all vectors and deleted {len(deleted_files)} file(s)"
    )

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to clear data: {e}")

# deletes all the vectors with certain pdf id
@app.post("/papers/delete")
async def delete_paper(payload: DeletePaperRequest):
  pdf_id = payload.pdf_id

  try:
    from ingest_paper import delete_paper_vectors
    delete_paper_vectors(pdf_id)

    pdf_path = TEST_PAPERS_DIR / f"{pdf_id}.pdf"
    if pdf_path.exists():
      pdf_path.unlink()

    # Remove from paper store
    paper_store.delete_paper(pdf_id)

    return {"status": "success", "message": f"Deleted paper: {pdf_id}"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to delete paper: {e}")

# gets all the papers uploaded
@app.get("/papers", response_model=List[PaperInfo])
async def list_papers():
  papers: List[PaperInfo] = []

  for pdf_path in TEST_PAPERS_DIR.glob("*pdf"):
    papers.append(
      PaperInfo(
        filename=pdf_path.name,
        pdf_id=pdf_path.stem,
        path=str(pdf_path.relative_to(BASE_DIR))
      )
    )
  
  return papers

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # we only rate limit the /ask endpoint
    if request.url.path == "/ask":
        client_id = request.client.host if request.client else "unknown"
        
        check = rate_limiter.check_rate_limit(client_id)
        
        if not check["allowed"]:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "detail": check["reason"],
                    "retry_after": check["retry_after"],
                },
                headers={"Retry-After": str(check["retry_after"])}
            )
        
        rate_limiter.record_request(client_id)
    
    response = await call_next(request)
    return response

# lists all active conversations
@app.get("/conversations", response_model=list[ConversationInfo])
async def list_conversations():
  return conversation_store.list_all()

# creates a new conversation
@app.get("/conversations/new")
async def create_conversation(pdf_ids: list[str] = None):
  conv = conversation_store.create(pdf_ids)
  return {"conversation_id": conv.id}

# deletes a conversation
@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
  if conversation_store.delete(conversation_id):
    return {"status": "success", "message": f"Deleted conversation {conversation_id}"}
  
  raise HTTPException(status_code=404, detail="Conversation not found")

# get the full conversation history
@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
  conv = conversation_store.get(conversation_id)
  if not conv:
    raise HTTPException(status_code=404, detail="Conversation not found")
  
  return {
    "conversation_id": conv.id,
    "messages": [m.to_dict() for m in conv.messages],
    "pdf_ids": conv.pdf_ids,
  }

@app.get("/stats/cache")
async def get_cache_stats():
  return embedding_cache.stats()

@app.get("/stats/rate-limit")
async def get_rate_limit_stats(request: Request):
  client_id = request.client.host if request.client else "unknown"
  return rate_limiter.get_remaining(client_id)

@app.post("/cache/clear")
async def clear_cache():
  embedding_cache.clear()
  return {"status": "success", "message": "Cache cleared"}

@app.post("/batch/upload", response_model=BatchUploadResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    domain: Optional[str] = None
):
    """
    Upload multiple PDF files for batch processing.
    Returns a job_id that can be used to track progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate all files are PDFs
    for f in files:
        if f.content_type not in ("application/pdf", "application/x-pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' is not a PDF. Only PDF files are allowed."
            )

    # Save files to disk and collect paths
    saved_paths: List[Path] = []
    try:
        for f in files:
            file_bytes = await f.read()

            if len(file_bytes) > 50 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{f.filename}' is too large. Maximum size is 50MB."
                )

            if not file_bytes.startswith(b'%PDF'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{f.filename}' is not a valid PDF."
                )

            safe_filename = f.filename.replace(" ", "_")
            dest_path = TEST_PAPERS_DIR / safe_filename
            dest_path.write_bytes(file_bytes)
            saved_paths.append(dest_path)

    except HTTPException:
        # Clean up any saved files on validation error
        for p in saved_paths:
            if p.exists():
                p.unlink()
        raise

    # Start batch processing in background
    job_id = process_batch(
        pdf_paths=saved_paths,
        ingest_paper=ingest_paper,
        store=batch_job_store,
        domain=domain,
    )

    return BatchUploadResponse(
        job_id=job_id,
        status="pending",
        file_count=len(saved_paths),
        message=f"Batch job started. Processing {len(saved_paths)} file(s)."
    )


@app.get("/batch/{job_id}/status", response_model=BatchJobStatus)
async def get_job_status(job_id: str):
    """
    Get the current status and progress of a batch job.
    """
    job = batch_job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Convert results to BatchJobResult format (exclude traceback for cleaner response)
    results = [
        BatchJobResult(
            pdf_path=r["pdf_path"],
            pdf_id=r.get("pdf_id", Path(r["pdf_path"]).stem),
            status=r["status"],
            error=r.get("error"),
            started_at=r.get("started_at"),
            completed_at=r.get("completed_at"),
        )
        for r in job.results
    ]

    return BatchJobStatus(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        pdf_paths=job.pdf_paths,
        results=results,
        created_at=job.created_at,
        completed_at=job.completed_at,
        domain=job.domain,
    )


@app.get("/batch/jobs")
async def list_batch_jobs():
    """
    List all batch jobs (newest first).
    """
    jobs = batch_job_store.list_jobs()
    return [job.to_dict() for job in jobs]


@app.post("/batch/ingest-folder", response_model=BatchUploadResponse)
async def ingest_folder(payload: FolderIngestRequest):
    """
    Start batch ingestion of all PDFs in a local folder.
    The folder path must be accessible from the server.
    """
    folder_path = Path(payload.folder_path)

    if not folder_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Folder '{payload.folder_path}' does not exist"
        )

    if not folder_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path '{payload.folder_path}' is not a directory"
        )

    # Find all PDF files in the folder
    pdf_files = list(folder_path.glob("*.pdf"))

    if not pdf_files:
        raise HTTPException(
            status_code=400,
            detail=f"No PDF files found in '{payload.folder_path}'"
        )

    # Start batch processing in background
    job_id = process_batch(
        pdf_paths=pdf_files,
        ingest_paper=ingest_paper,
        store=batch_job_store,
        domain=payload.domain,
    )

    return BatchUploadResponse(
        job_id=job_id,
        status="pending",
        file_count=len(pdf_files),
        message=f"Batch job started. Processing {len(pdf_files)} file(s) from folder."
    )

# cluster papers to identify thematic groups
@app.post("/literature-review/cluster", response_model=ClusterResponse)
async def cluster_papers(payload: ClusterRequest):
    try:
        pdf_ids = payload.pdf_ids or get_all_pdf_ids()
        
        if len(pdf_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 papers for clustering"
            )
        
        params = payload.params or {}
        
        # Map method to parameters
        if payload.method == "kmeans":
            n_clusters = params.get("n_clusters", max(2, len(pdf_ids) // 3))
            params = {"n_clusters": n_clusters}
        elif payload.method == "hierarchical":
            params = {
                "n_clusters": params.get("n_clusters"),
                "distance_threshold": params.get("distance_threshold", 0.5),
            }
        elif payload.method == "dbscan":
            params = {
                "eps": params.get("eps", 0.3),
                "min_samples": params.get("min_samples", 2),
            }
        
        result = analyze_paper_collection(
            pdf_ids=pdf_ids,
            clustering_method=payload.method,
            n_clusters=params.get("n_clusters"),
            extract_topics=True,
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ClusterResponse(
            method=result["method"],
            total_papers=result["total_papers"],
            num_clusters=result["num_clusters"],
            clusters=result["clusters"],
            outliers=result.get("outliers"),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")

# find papers similar to the specified paper
@app.get("/literature-review/similar/{pdf_id}")
async def get_similar_papers(pdf_id: str, top_k: int = 5):
    try:
        similar = find_similar_papers(pdf_id, top_k=top_k)
        
        return {
            "query_paper": pdf_id,
            "similar_papers": [
                {
                    "pdf_id": s.pdf_id,
                    "similarity_score": round(s.similarity_score, 4),
                }
                for s in similar
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


# compare 2-5 papers to identify similarities and differences
@app.post("/literature-review/compare", response_model=CompareResponse)
async def compare_papers_endpoint(payload: CompareRequest):
    if len(payload.pdf_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 papers to compare")
    if len(payload.pdf_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 papers can be compared at once")
    
    try:
        result = compare_papers(payload.pdf_ids)
        
        return CompareResponse(
            pdf_ids=result.pdf_ids,
            similarities=result.similarities,
            differences=result.differences,
            key_themes=result.key_themes,
            methodology_comparison=result.methodology_comparison,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

# synthesize findings across multiple papers
@app.post("/literature-review/synthesize", response_model=SynthesizeResponse)
async def synthesize_papers(payload: SynthesizeRequest):
    if not payload.pdf_ids:
        raise HTTPException(status_code=400, detail="No papers provided")
    
    try:
        result = synthesize_findings(
            pdf_ids=payload.pdf_ids,
            focus_question=payload.focus_question,
        )
        
        return SynthesizeResponse(
            synthesis=result.synthesis,
            citations=result.citations,
            methodology_comparison=result.methodology_comparison,
            findings_comparison=result.findings_comparison,
            papers_analyzed=result.papers_analyzed,
            confidence=result.confidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

# summarize the methodology section of a paper
@app.get("/literature-review/methodology/{pdf_id}")
async def get_methodology_summary(pdf_id: str):
    try:
        result = extract_methodology_summary(pdf_id)

        if result.get("error"):
            raise HTTPException(
                status_code=404,
                detail=f"Could not extract methodology: {result['error']}"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Methodology extraction failed: {str(e)}")


# -------- Paper Metadata Endpoints --------

@app.get("/papers/{pdf_id}/metadata", response_model=PaperMetadataResponse)
async def get_paper_metadata(pdf_id: str):
    """Get detailed metadata for a specific paper."""
    paper = paper_store.get_paper(pdf_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper '{pdf_id}' not found")

    return PaperMetadataResponse(
        pdf_id=paper.pdf_id,
        filename=paper.filename,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        domain=paper.domain,
        upload_date=paper.upload_date,
        chunk_count=paper.chunk_count,
    )


@app.get("/papers/metadata", response_model=List[PaperMetadataResponse])
async def list_papers_metadata():
    """Get metadata for all papers."""
    papers = paper_store.list_papers()
    return [
        PaperMetadataResponse(
            pdf_id=p.pdf_id,
            filename=p.filename,
            title=p.title,
            abstract=p.abstract,
            authors=p.authors,
            domain=p.domain,
            upload_date=p.upload_date,
            chunk_count=p.chunk_count,
        )
        for p in papers
    ]


# -------- Cluster Persistence Endpoints --------

@app.post("/clusters/save", response_model=ClusteringSessionResponse)
async def save_clustering_result(payload: SaveClusterRequest):
    """Save a clustering result for later reference."""
    session = cluster_store.save_clustering_result(
        name=payload.name,
        method=payload.method,
        clusters=payload.clusters,
        total_papers=payload.total_papers,
        outliers=payload.outliers,
    )

    return ClusteringSessionResponse(
        session_id=session.session_id,
        name=session.name,
        method=session.method,
        clusters=[
            SavedClusterResponse(
                cluster_id=c.cluster_id,
                name=c.name,
                pdf_ids=c.pdf_ids,
                topics=c.topics,
                method=c.method,
                created_at=c.created_at,
            )
            for c in session.clusters
        ],
        total_papers=session.total_papers,
        outliers=session.outliers,
        created_at=session.created_at,
    )


@app.get("/clusters/sessions", response_model=List[ClusteringSessionResponse])
async def list_saved_sessions():
    """List all saved clustering sessions."""
    sessions = cluster_store.list_sessions()
    return [
        ClusteringSessionResponse(
            session_id=s.session_id,
            name=s.name,
            method=s.method,
            clusters=[
                SavedClusterResponse(
                    cluster_id=c.cluster_id,
                    name=c.name,
                    pdf_ids=c.pdf_ids,
                    topics=c.topics,
                    method=c.method,
                    created_at=c.created_at,
                )
                for c in s.clusters
            ],
            total_papers=s.total_papers,
            outliers=s.outliers,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@app.get("/clusters/sessions/{session_id}", response_model=ClusteringSessionResponse)
async def get_saved_session(session_id: str):
    """Get a specific saved clustering session."""
    session = cluster_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return ClusteringSessionResponse(
        session_id=session.session_id,
        name=session.name,
        method=session.method,
        clusters=[
            SavedClusterResponse(
                cluster_id=c.cluster_id,
                name=c.name,
                pdf_ids=c.pdf_ids,
                topics=c.topics,
                method=c.method,
                created_at=c.created_at,
            )
            for c in session.clusters
        ],
        total_papers=session.total_papers,
        outliers=session.outliers,
        created_at=session.created_at,
    )


@app.patch("/clusters/sessions/{session_id}")
async def rename_session(session_id: str, payload: RenameClusterRequest):
    """Rename a saved clustering session."""
    session = cluster_store.rename_session(session_id, payload.new_name)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {"status": "success", "message": f"Session renamed to '{payload.new_name}'"}


@app.patch("/clusters/sessions/{session_id}/clusters/{cluster_id}")
async def rename_cluster(session_id: str, cluster_id: str, payload: RenameClusterRequest):
    """Rename a cluster within a session."""
    cluster = cluster_store.rename_cluster(session_id, cluster_id, payload.new_name)
    if not cluster:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster '{cluster_id}' not found in session '{session_id}'"
        )

    return {"status": "success", "message": f"Cluster renamed to '{payload.new_name}'"}


@app.delete("/clusters/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a saved clustering session."""
    if cluster_store.delete_session(session_id):
        return {"status": "success", "message": f"Session '{session_id}' deleted"}

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")