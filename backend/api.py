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
from cache import embedding_cache, rate_limiter
from batch_processor import batch_job_store, process_batch

from literature_review import (
    compare_papers,
    synthesize_findings,
    analyze_literature,
    extract_methodology_summary,
    generate_review_report,
)

from clustering import (
    find_similar_papers,
    analyze_paper_collection,
    get_all_pdf_ids,
)

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

class ReviewRequest(BaseModel):
    pdf_ids: List[str]
    title: Optional[str] = None
    format: str = "markdown"  # "markdown" or "json"

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

    ingest_paper(dest_path, pdf_id=safe_filename.replace(".pdf", ""), clear_existing=False, domain=domain)
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