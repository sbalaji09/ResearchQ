# Backend-only Dockerfile for Railway
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (including OpenCV requirements for unstructured)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Create data directories
RUN mkdir -p /app/backend/data /app/backend/test_papers

# Set working directory to backend for correct imports
WORKDIR /app/backend

# Default port (Railway overrides via $PORT env var)
ENV PORT=8000
EXPOSE 8000

# Run the FastAPI server
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
