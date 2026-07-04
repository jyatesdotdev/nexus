# Stage 1: Builder
# We use a builder stage to install dependencies and keep the final image clean.
FROM python:3.14-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies if needed (e.g., for psycopg2 from source)
# EDUCATIONAL NOTE: psycopg2-binary usually doesn't need these, but it's good practice
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into a dedicated path to copy easily to the final stage
COPY nexus-mcp/requirements.txt .
COPY nexus-common /nexus-common
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Final
# This is the lightweight image that will be deployed.
FROM python:3.14-slim

# Re-establish environment variables for the final stage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PROMETHEUS_MULTIPROC_DIR="/tmp/prometheus_multiproc"

# Create a non-root user with a fixed UID/GID for consistent permissions
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/sh -m appuser

WORKDIR /app

# Create multiproc dir and assign permissions
RUN mkdir -p $PROMETHEUS_MULTIPROC_DIR && chown -R appuser:appuser $PROMETHEUS_MULTIPROC_DIR

# Copy only the installed dependencies from the builder stage
COPY --from=builder /install /usr/local
COPY --from=builder /nexus-common /nexus-common

# Copy the application source code and set ownership in a single layer
# The .dockerignore ensures we don't copy venv, tests, or cache files
COPY --chown=appuser:appuser nexus-mcp/ .

# Ensure the appuser has access to the workspace
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the MCP server port
EXPOSE 8000

# Healthcheck to ensure the server is responsive
# We use a simple python command to check if the port is open
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s = socket.socket(); s.connect(('localhost', 8000)); s.close()"

# Start the MCP HR Directory Server
CMD ["/bin/sh", "-c", "rm -rf /tmp/prometheus_multiproc/* && python server.py"]
