# Stage 1: Builder
FROM python:3.14-slim AS builder

# Build-time metadata
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (necessary for compiling some Python C-extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and use virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies separately to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Final Runtime
FROM python:3.14-slim

# Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application source
COPY orchestrator/ ./orchestrator/
COPY main.py .

# Ensure the appuser owns the application files
RUN chown -R appuser:appuser /app
USER appuser

# Standard port for the orchestrator
EXPOSE 8080

# Use Gunicorn with Uvicorn workers for production-grade concurrency
# --bind 0.0.0.0:8080 allows external traffic
# --workers 4 (Adjust based on CPU cores in production)
CMD ["gunicorn", "orchestrator.app:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-"]
