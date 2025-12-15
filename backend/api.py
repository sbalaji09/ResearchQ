from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ingest_paper import ingest_paper          # <-- change if needed

app = FastAPI(
    title="ResearchQ Backend",
    description="API server for uploading papers and asking questions.",
)

# add the deployed frontend origin later
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # or ["*"] during early dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
TEST_PAPERS_DIR = BASE_DIR / "test_papers"
TEST_PAPERS_DIR.mkdir(exist_ok=True)


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

# accepts a single PDF upload and saves it to test_papers
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # normalize filename
    safe_filename = file.filename.replace(" ", "_")
    dest_path = TEST_PAPERS_DIR / safe_filename

    try:
        # save file to disk
        file_bytes = await file.read()
        dest_path.write_bytes(file_bytes)

        ingest_paper(dest_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")

    return UploadResponse(status="success", filename=safe_filename)
