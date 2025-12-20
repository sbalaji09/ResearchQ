import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone

from ingest_paper import ingest_paper
from query_improved import content_generator
from conversation import conversation_store, Conversation

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
  suggestion: str = None

class AskResponse(BaseModel):
  answer: str
  citations: list[Citation] = []
  warning: str = None
  confidence: str = None
  error: ErrorDetail = None
  conversation_id: str = None

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

class ConversationInfo(BaseModel):
  id: str
  message_count: int
  created_at: str
  last_active: str
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

    if len(file_bytes) > 50 * 1024 * 1024:
      raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
    
    if not file_bytes.startswith(b'%PDF'):
      raise HTTPException(status_code=400, detail="Invalid PDF file.")
    
    dest_path.write_bytes(file_bytes)

    ingest_paper(dest_path, pdf_id=safe_filename.replace(".pdf", ""), clear_existing=False)
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
