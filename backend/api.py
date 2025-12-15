from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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