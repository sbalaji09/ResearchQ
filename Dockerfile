# Lightweight Backend Dockerfile for Render/Railway deployment
FROM python:3.12-slim

WORKDIR /app

# Install minimal system dependencies
# Only what's needed for pdfplumber and basic operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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

# Default port (Render uses 10000, Railway uses 8000 - both override via $PORT env var)
ENV PORT=10000
EXPOSE 10000

# Run the FastAPI server
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
