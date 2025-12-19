import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone

from ingest_paper import ingest_paper
from query_improved import content_generator

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

class Citation(BaseModel):
    id: int
    document: str
    section: str
    text: str

class ErrorDetail(BaseModel):
  error_code: str
  message: str
  suggestion: str = None
  
class AskResponse(BaseModel):
  answer: str
  citations: list[Citation] = []
  warning: str = None
  confidence: str = None
  error: ErrorDetail = None

class UploadResponse(BaseModel):
  status: str
  filename: str

class PaperInfo(BaseModel):
  filename: str
  path: str

class ClearResponse(BaseModel):
  status: str
  message: str

class DeletePaperRequest(BaseModel):
  pdf_id: str

# ---------------- Routes ----------------

@app.get("/")
async def root():
  return {"status": "ok", "message": "ResearchQ backend is running"}

# accepts a single PDF file and saves it to the backend/test_papers
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
  if file.content_type not in ("application/pdf", "application/x-pdf"):
    raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

  safe_filename = file.filename.replace(" ", "_")
  dest_path = TEST_PAPERS_DIR / safe_filename

  try:
    file_bytes = await file.read()
    dest_path.write_bytes(file_bytes)

    ingest_paper(dest_path, pdf_id=safe_filename.replace(".pdf", ""), clear_existing=False)

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")

  return UploadResponse(status="success", filename=safe_filename)

# accepts JSON and uses RAG pipeline to answer
@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
  question = payload.question.strip()
  if not question:
    raise HTTPException(status_code=400, detail="Question cannot be empty.")

  try:
    result = content_generator(question, pdf_ids=payload.pdf_ids)

    answer = result.get("answer", "")
    citations = result.get("citations", [])

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("content_generator returned an empty or invalid answer")
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}")

  return AskResponse(answer=answer, citations=citations)

# list PDFs saved in backend/test_papers
@app.get("/papers", response_model=List[PaperInfo])
async def list_papers():
  papers: List[PaperInfo] = []

  for pdf_path in TEST_PAPERS_DIR.glob("*.pdf"):
    papers.append(
      PaperInfo(
        filename=pdf_path.name,
        path=str(pdf_path.relative_to(BASE_DIR)),
      )
    )

  return papers


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