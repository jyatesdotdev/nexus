# nexus-stack/scripts

Operational shell scripts behind the Makefile targets in `..`. All are bash, invoked as
`make doctor`, `make demo`, and `make new-agent NAME=<name>` — prefer the make targets;
run the scripts directly only when debugging them. Verify edits with `bash -n <script>`.

## Files at this level

- `doctor.sh` (`make doctor`) — preflight checks with fix suggestions: docker CLI +
  daemon, `.env` exists with a non-placeholder `GEMINI_API_KEY` (presence is tested with
  `grep -q` only; the value is never read into a variable or printed — preserve that
  property when editing), the external `nexus-net` network, node/npm (the UI builds on
  the host), and uv (test/lint targets run through the workspace). Exits nonzero if any
  check fails.
- `demo.sh` (`make demo`) — guided three-prompt conversation against a RUNNING stack
  (MCP delegation, A2A weather, local sensor tool), printing each answer plus its
  `X-Trace-Id` and a Grafana Tempo link. Reads `ORCHESTRATOR_HOST_PORT` from `../.env`
  (the only var it reads from that file — keep it that way; `.env` holds a real API key)
  and honors `ORCH_URL` / `GRAFANA_URL` overrides. Prompts mirror
  `nexus-orchestrator/orchestrator/eval_cases.py` and deliberately avoid human-in-the-loop
  triggers (they would stall a headless script). SSE parsing is embedded stdlib-only
  python3.
- `new-agent.sh` (`make new-agent NAME=<name> [PORT=<port>]`) — scaffolds a new A2A
  sub-agent at `../../nexus-<name>` from `../templates/a2a-service/` by token
  substitution (see `../templates/AGENTS.md` for the token table). Validates NAME
  (`^[a-z][a-z0-9-]*$`), refuses to overwrite an existing directory, auto-picks the next
  free 800x port, and prints the manual join-the-system checklist (compose snippet,
  `A2A_AGENT_URLS` append, Prometheus scrape target, uv workspace member) rather than
  editing shared files itself.

## Caution

- Never print `.env` values in any of these scripts.
- `sed -i` usage in new-agent.sh is BSD/GNU-portable (`-i.bak` + cleanup); keep it that
  way — this repo is developed on macOS.
