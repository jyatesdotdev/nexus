# Builder Stage
FROM python:3.14-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final Stage
FROM python:3.14-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install them
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

# Add a native healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/.well-known/agent-card.json || exit 1

# Use Gunicorn with Uvicorn workers for production readiness
CMD ["gunicorn", "server:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001"]
