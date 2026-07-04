#!/usr/bin/env bash
# EDUCATIONAL NOTE: Preflight ("doctor") scripts catch environment problems before
# a long `make up` fails halfway through. We check every prerequisite, report ALL
# problems in one pass (rather than stopping at the first), and exit nonzero so
# CI or a human knows the machine is not ready.
#
# Secrets hygiene: this script only tests for the PRESENCE of GEMINI_API_KEY with
# grep -q; the value itself is never read into a variable, echoed, or logged.

set -u

STACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$STACK_DIR/.env"
FAILURES=0

ok()   { printf '  [OK]   %s\n' "$1"; }
fail() {
  printf '  [FAIL] %s\n' "$1"
  printf '         fix: %s\n' "$2"
  FAILURES=$((FAILURES + 1))
}

echo "Nexus stack preflight (make doctor)"
echo "-----------------------------------"

# 1. Docker CLI + daemon
DOCKER_OK=0
if command -v docker >/dev/null 2>&1; then
  ok "docker CLI installed"
  if docker info >/dev/null 2>&1; then
    ok "docker daemon is running"
    DOCKER_OK=1
  else
    fail "docker daemon is not running" \
         "start Docker Desktop (or the docker service) and re-run 'make doctor'"
  fi
else
  fail "docker CLI not found" \
       "install Docker Desktop: https://docs.docker.com/get-docker/"
fi

# 2. .env exists and GEMINI_API_KEY is set to a non-placeholder value
if [ -f "$ENV_FILE" ]; then
  ok ".env exists"
  # Presence-only check: -q suppresses output so the key value is never printed.
  if grep -Eq '^GEMINI_API_KEY=..*' "$ENV_FILE" \
     && ! grep -Eiq '^GEMINI_API_KEY=(your|changeme|placeholder|xxx|<)' "$ENV_FILE"; then
    ok "GEMINI_API_KEY is set (value not shown)"
  else
    fail "GEMINI_API_KEY is missing or still a placeholder in .env" \
         "edit .env and paste a real key from https://aistudio.google.com/"
  fi
else
  fail ".env not found in nexus-stack/" \
       "run: cp .env.example .env   then add your GEMINI_API_KEY"
fi

# 3. External Docker network shared with ../nexus-dev-infra
if [ "$DOCKER_OK" -eq 1 ]; then
  if docker network inspect nexus-net >/dev/null 2>&1; then
    ok "external Docker network 'nexus-net' exists"
  else
    fail "external Docker network 'nexus-net' does not exist" \
         "'make up' creates it automatically (or: docker network create nexus-net)"
  fi
else
  fail "cannot check the 'nexus-net' network" \
       "resolve the Docker problems above first"
fi

# 4. Node.js + npm (the UI is built on the host before its nginx image is built)
if command -v node >/dev/null 2>&1; then
  ok "node installed ($(node --version))"
else
  fail "node not found (required: 'make build' compiles ../nexus-ui on the host)" \
       "install Node.js: https://nodejs.org/ (or 'brew install node')"
fi
if command -v npm >/dev/null 2>&1; then
  ok "npm installed ($(npm --version))"
else
  fail "npm not found (required to build ../nexus-ui)" \
       "npm ships with Node.js — install Node.js first"
fi

echo "-----------------------------------"
if [ "$FAILURES" -eq 0 ]; then
  echo "All checks passed. Next: make up, then make demo."
  exit 0
else
  echo "$FAILURES problem(s) found — fix the items above and re-run 'make doctor'."
  exit 1
fi
