#!/usr/bin/env bash
# EDUCATIONAL NOTE: A scripted "guided tour" is the fastest way to showcase a
# multi-agent system: it sends canned prompts that each exercise a different
# integration path (MCP delegation, A2A delegation, local tools) and surfaces
# the observability story (trace IDs -> Grafana Tempo) alongside the answers.
#
# Prompt selection: these phrasings mirror the orchestrator's eval suite
# (nexus-orchestrator/orchestrator/eval_cases.py), so routing is known-good.
# We deliberately AVOID prompts that trigger human-in-the-loop approval
# (e.g. "delete user X" via the MCP admin tool) — a HITL confirmation pauses
# the stream waiting for a UI button click, which would stall this headless script.
#
# No dependencies beyond curl + python3 (stdlib only).

set -euo pipefail

ORCH_URL="${ORCH_URL:-http://localhost:8080}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

# Preflight: is the orchestrator up?
if ! curl -sf --max-time 5 "$ORCH_URL/health" >/dev/null 2>&1; then
  echo "The orchestrator is not responding at $ORCH_URL/health."
  echo "Start the stack first:"
  echo "  make up      # starts infra + app services"
  echo "  make logs    # wait until the orchestrator reports healthy"
  echo "then re-run: make demo"
  exit 1
fi

# EDUCATIONAL NOTE: `python3 -` reads the program from stdin (this heredoc);
# extra arguments after `-` become sys.argv. The quoted 'PYEOF' delimiter
# disables shell interpolation so the Python code is passed through verbatim.
exec python3 - "$ORCH_URL" "$GRAFANA_URL" <<'PYEOF'
# EDUCATIONAL NOTE: We parse the orchestrator's Server-Sent Events (SSE) stream
# the same way the React UI does (nexus-ui/src/App.tsx): each `data: ` line is
# a JSON event; `partial: true` events are text deltas to append, while
# non-partial events carry the full authoritative text (replace, don't append).
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

ORCH = sys.argv[1].rstrip("/")
GRAFANA = sys.argv[2].rstrip("/")

# Mock JWT accepted by the orchestrator's identity middleware: it only checks
# for three dot-separated parts with a header starting in "eyJ" (see
# nexus-common/nexus_common/auth.py). The middle segment becomes the user id.
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.demo_user.mock_signature"
SESSION_ID = f"demo_{uuid.uuid4().hex[:8]}"

# (label, prompt) pairs — phrasings match eval_cases.py for reliable routing.
DEMO_STEPS = [
    ("MCP delegation — HR directory (nexus-mcp)",
     "Who works in the engineering department?"),
    ("A2A delegation — weather agent (nexus-a2a)",
     "What is the weather like in Tokyo today?"),
    ("Local tool — sensor agent (orchestrator built-in)",
     "Get the latest reading from sensor SENSOR_789."),
]


def tempo_link(trace_id):
    """Grafana Explore deep-link that opens the trace in the Tempo datasource."""
    left = json.dumps({
        "datasource": "tempo",
        "queries": [{"query": trace_id, "queryType": "traceql"}],
    })
    return f"{GRAFANA}/explore?left={urllib.parse.quote(left)}"


def run_prompt(prompt):
    """POST one prompt to /run_sse, stream the SSE reply, return (text, trace_id)."""
    body = json.dumps({
        "app_name": "containerized_agents",
        "user_id": TOKEN,
        "session_id": SESSION_ID,
        "streaming": True,
        "new_message": {"role": "user", "parts": [{"text": prompt}]},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{ORCH}/run_sse",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = urllib.request.urlopen(request, timeout=180)
    trace_id = response.headers.get("X-Trace-Id")

    accumulated = ""
    announced = ""
    for raw_line in response:
        line = raw_line.decode("utf-8", "replace").rstrip("\r\n")
        if not line.startswith("data: "):
            continue
        try:
            event = json.loads(line[len("data: "):])
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        # Show delegation hops (root agent -> sub-agent) as they happen.
        target = (event.get("actions") or {}).get("transferToAgent")
        if target and target != announced:
            announced = target
            print(f"  ... delegating to {target}")

        parts = (event.get("content") or {}).get("parts") or []
        text = "".join(p.get("text") or "" for p in parts if isinstance(p, dict))
        if not text:
            continue
        if event.get("partial") is True:
            accumulated += text  # streaming delta
        else:
            accumulated = text   # final authoritative text
    return accumulated.strip(), trace_id


print("Nexus guided demo")
print(f"  orchestrator : {ORCH}")
print(f"  session      : {SESSION_ID}")

failures = 0
for index, (label, prompt) in enumerate(DEMO_STEPS, start=1):
    print()
    print(f"[{index}/{len(DEMO_STEPS)}] {label}")
    print(f"  You  > {prompt}")
    try:
        answer, trace_id = run_prompt(prompt)
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace")
        print(f"  ERROR: HTTP {exc.code} from /run_sse: {detail}")
        failures += 1
        continue
    except OSError as exc:
        print(f"  ERROR: could not reach the orchestrator: {exc}")
        failures += 1
        continue

    if answer:
        for answer_line in answer.splitlines():
            print(f"  Nexus> {answer_line}")
    else:
        print("  Nexus> (no text in response stream)")
        failures += 1

    if trace_id:
        print(f"  Trace> X-Trace-Id: {trace_id}")
        print(f"         {tempo_link(trace_id)}")
    else:
        print("  Trace> (no X-Trace-Id header on this response —"
              f" browse traces in Grafana Tempo: {GRAFANA}/explore)")

print()
if failures:
    print(f"Demo finished with {failures} failed step(s) — check 'make logs'.")
    sys.exit(1)
print(f"Demo complete. Explore the chat UI at http://localhost:5173 and traces at {GRAFANA}.")
PYEOF
