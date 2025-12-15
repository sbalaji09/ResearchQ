from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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