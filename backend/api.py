from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 👇 Adjust these imports to match your actual filenames
# e.g. if you have backend/ingest_paper.py with def ingest_paper(pdf_path: Path): ...
# and backend/rag_pipeline.py with def content_generator(question: str) -> str: ...
from ingest_paper import ingest_paper
from query_improved import content_generator

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


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
    # add your deployed frontend domain later, e.g.:
    # "https://your-frontend-domain.com",
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


class AskResponse(BaseModel):
  answer: str


class UploadResponse(BaseModel):
  status: str
  filename: str


class PaperInfo(BaseModel):
  filename: str
  path: str


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

    ingest_paper(dest_path, pdf_id=safe_filename.replace(".pdf", ""), clear_existing=True)

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
    answer = content_generator(question)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to generate answer: {e}")

  return AskResponse(answer=answer)

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
