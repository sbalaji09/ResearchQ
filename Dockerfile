FROM python:3.13-slim

WORKDIR /app

# system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# backend requirements + install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# backend code
COPY backend/ ./backend/

# data directory for JSON storage
RUN mkdir -p /app/backend/data /app/backend/test_papers

# port
EXPOSE 8000

# run fastapi server
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]