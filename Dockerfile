# Use Python 3.11-slim as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
# - libgomp1 is required by faiss-cpu (OpenMP runtime library)
# - ca-certificates is required to connect securely to remote SSL databases like PlanetScale
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port (Railway will override this via the PORT environment variable)
EXPOSE 8000

# Start FastAPI application using uvicorn with dynamic port expansion
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
