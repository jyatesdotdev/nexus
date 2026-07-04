# EDUCATIONAL NOTE: Nexus container standards in one file — a multi-stage build
# (wheels built in a throwaway layer keep the runtime image lean), a non-root
# user, and a native HEALTHCHECK. The build context must be the workspace
# parent directory (it copies the sibling nexus-common checkout), which is how
# nexus-stack/docker-compose.yml invokes every service Dockerfile (context: ..).

# Builder Stage
FROM python:3.14-slim AS builder

WORKDIR /build

COPY nexus-__SERVICE_NAME__/requirements.txt .
COPY nexus-common /nexus-common
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Final Stage
FROM python:3.14-slim

ENV PROMETHEUS_MULTIPROC_DIR="/tmp/prometheus_multiproc"

# Create a non-root user for security
RUN groupadd -r appuser && useradd -m -r -g appuser appuser

WORKDIR /app

# Create multiproc dir and assign permissions
RUN mkdir -p $PROMETHEUS_MULTIPROC_DIR && chown -R appuser:appuser $PROMETHEUS_MULTIPROC_DIR

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install them
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY nexus-__SERVICE_NAME__/ .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE __PORT__

# Add a native healthcheck (the agent card doubles as a readiness probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:__PORT__/.well-known/agent-card.json || exit 1

# Use Gunicorn with Uvicorn workers for production readiness
CMD ["/bin/sh", "-c", "rm -rf /tmp/prometheus_multiproc/* && gunicorn server:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:__PORT__"]
