#!/usr/bin/env bash
#
# new-agent.sh — scaffold a new A2A sub-agent service from
# nexus-stack/templates/a2a-service into ../nexus-<name>.
#
# Usage:  bash scripts/new-agent.sh <name> [port]
# Normally invoked via:  make new-agent NAME=<name> [PORT=<port>]
#
# EDUCATIONAL NOTE: Scaffolding vs. auto-wiring
# [Why] This script deliberately only CREATES the new service directory and
# then PRINTS the remaining wiring steps (compose entry, A2A_AGENT_URLS,
# Prometheus scrape target, uv workspace member) instead of editing those
# shared files itself. Those files are contracts between services — a human
# should review each change — and walking the checklist teaches exactly how a
# service joins the system.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE_DIR="$(dirname "$STACK_DIR")"
TEMPLATE_DIR="$STACK_DIR/templates/a2a-service"

NAME="${1:-}"
PORT="${2:-}"

fail() {
  echo "❌ $1" >&2
  exit 1
}

[ -n "$NAME" ] || fail "NAME is required. Usage: make new-agent NAME=<name> [PORT=<port>]"
[[ "$NAME" =~ ^[a-z][a-z0-9-]*$ ]] || fail "NAME must be lowercase letters/digits/hyphens, starting with a letter (got: '$NAME')."
[ -d "$TEMPLATE_DIR" ] || fail "Template not found at $TEMPLATE_DIR"

TARGET_DIR="$WORKSPACE_DIR/nexus-$NAME"
# Refuse to overwrite anything that already exists (including existing
# services like nexus-a2a, nexus-mcp, ...).
[ ! -e "$TARGET_DIR" ] || fail "$TARGET_DIR already exists — refusing to overwrite. Pick another NAME or remove the directory first."

# Default port: first free 800x, judged against every port number already
# mentioned in the app-stack compose file and the Prometheus scrape config.
if [ -z "$PORT" ]; then
  USED_PORTS="$(grep -hoE '[0-9]{4,5}' \
    "$STACK_DIR/docker-compose.yml" \
    "$WORKSPACE_DIR/nexus-dev-infra/prometheus.yml" 2>/dev/null | sort -u || true)"
  PORT=8002
  while grep -qx "$PORT" <<<"$USED_PORTS"; do
    PORT=$((PORT + 1))
  done
fi
[[ "$PORT" =~ ^[0-9]+$ ]] || fail "PORT must be numeric (got: '$PORT')."

# Derived token values (see templates/AGENTS.md for the token table).
SNAKE="${NAME//-/_}"
UPPER="$(tr '[:lower:]' '[:upper:]' <<<"$SNAKE")"
TITLE=""
IFS='-' read -r -a NAME_PARTS <<<"$NAME"
for part in "${NAME_PARTS[@]}"; do
  TITLE+="$(tr '[:lower:]' '[:upper:]' <<<"${part:0:1}")${part:1}"
done
TODAY="$(date +%Y-%m-%d)"

echo "🧬 Scaffolding nexus-$NAME (port $PORT, agent class ${TITLE}AgentExecutor)..."
cp -R "$TEMPLATE_DIR" "$TARGET_DIR"

# Substitute tokens in every copied file. `sed -i.bak` + rm works on both
# BSD (macOS) and GNU sed, unlike a bare `sed -i`.
find "$TARGET_DIR" -type f | while IFS= read -r file; do
  sed -i.bak \
    -e "s/__SERVICE_NAME__/$NAME/g" \
    -e "s/__SERVICE_SNAKE__/$SNAKE/g" \
    -e "s/__SERVICE_UPPER__/$UPPER/g" \
    -e "s/__SERVICE_TITLE__/$TITLE/g" \
    -e "s/__PORT__/$PORT/g" \
    -e "s/__DATE__/$TODAY/g" \
    "$file"
  rm -f "$file.bak"
done

CARD_URL="http://$NAME-agent:$PORT/.well-known/agent-card.json"

cat <<EOF

✅ Created $TARGET_DIR

Next steps to wire nexus-$NAME into the stack:

1. Add the service to nexus-stack/docker-compose.yml (paste under 'services:'):

  $NAME-agent:
    # EDUCATIONAL NOTE: A2A sub-agent scaffolded from nexus-stack/templates/a2a-service.
    restart: unless-stopped
    build:
      context: ..
      dockerfile: nexus-$NAME/Dockerfile
    ports:
      - "$PORT:$PORT"
    volumes:
      - ../nexus-$NAME:/app
      - ../nexus-common:/nexus-common
    environment:
      - ${UPPER}_HOST=0.0.0.0
      - ${UPPER}_PORT=$PORT
      - ${UPPER}_PUBLIC_URL=http://$NAME-agent:$PORT
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4319
      - OTEL_METRICS_EXPORTER=none
      - OTEL_LOGS_EXPORTER=none
      - OTEL_SERVICE_NAME=$NAME-agent
    networks:
      - nexus-net
    healthcheck:
      test: ["CMD-SHELL", "python3 -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:$PORT/.well-known/agent-card.json\")' || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 5

2. Tell the orchestrator about the new agent: in the 'orchestrator' service's
   environment (same file), add A2A_AGENT_URLS with the existing card plus
   yours (comma-separated; it overrides the single-URL default):

      - A2A_AGENT_URLS=http://a2a-agent:8001/.well-known/agent-card.json,$CARD_URL

   The orchestrator fetches each card at startup and registers one sub-agent
   per card, named from the card's 'name' field. Optionally also add
   '$NAME-agent' to the orchestrator's depends_on with
   'condition: service_healthy'.

3. Add a Prometheus scrape target in ../nexus-dev-infra/prometheus.yml:

      - job_name: '$NAME-agent'
        static_configs:
          - targets: ['$NAME-agent:$PORT']

4. Add "nexus-$NAME" to [tool.uv.workspace] members in the workspace-root
   pyproject.toml, then run 'uv sync' from the workspace root.

5. Verify the scaffold:  cd ../nexus-$NAME && uv run pytest tests/ && uv run ruff check .

6. Implement your capability: edit process_query() in ../nexus-$NAME/server.py
   (look for the TODO) and update the AgentCard name/description/skills —
   the card 'name' becomes the orchestrator-side agent name.

7. Housekeeping: add "nexus-$NAME/**" to the include list in
   nexus-stack/.semgrep.yaml (so 'make verify-all' enforces standards on it)
   and add the directory to the root AGENTS.md map.

8. Run it:  make build && make up   — then check
   http://localhost:$PORT/.well-known/agent-card.json and ask the orchestrator
   something only your new agent can answer.
EOF
