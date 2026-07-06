# The Journey: How This Lab Got Here

Nexus is a lab about agents communicating — and its own history is the best case study
it owns. This is the honest story of how it was built, broken, rediscovered, repaired,
and published, reconstructed from git history, changelogs, and the working notes of the
AI agents that did much of the later work. Nothing here is embellished; every incident
below is preserved in a commit, a test, or a code comment you can still read.

## Prologue: one repo, one idea (March 2026)

The project began as a single repository — an "agent orchestration lab" with everything
under `src/agent_app/`. The educational DNA was there from the first commits: a
changelog entry from **2026-03-21** already talks about explaining "the Why and How" of
the architecture, and the original TODO list shows something prophetic — *sub-agents
were used to write the documentation* for each component. This project has never not
been built with agents.

## Chapter 1: The Branded Split (March 24)

On a single day, the monolith became six repositories, each with an "Initial commit:
Nexus Branded Split": the orchestrator, the MCP HR server, the A2A weather agent, the
React frontend, the integration tests, and the deployment stack. The ambition was
textbook microservices: independently deployable, independently versioned.

Reality was messier. Two repos were later renamed (`nexus-directory` → `nexus-mcp`,
`nexus-weather` → `nexus-a2a`), leaving empty tombstone directories behind. A shared
library (`nexus-common`) and the observability stack never got version control at all.
A feature era followed — identity propagation, an admin-gated `delete_user`, the
reviewer pattern — and then the project went quiet for roughly three months. Working
trees silently accumulated large uncommitted restructures. Docs drifted from code.
Virtualenvs broke as directories were renamed underneath their shebangs.

## Chapter 2: The audit (July 3)

Work resumed with a question — *"it's a bit of a mess, what would you clean up?"* — and
a rule that shaped everything after: **documentation should live where an agent lands.**
Every directory got an `AGENTS.md` describing the files at that level, written for a
reader with no other context. Parallel agents converted the old docs, verifying every
claim against the code instead of copying it — and the drift they found was the real
audit:

- The docs described functions, files, and layouts that no longer existed.
- The venv shebangs still pointed at the pre-rename paths — solving the mystery of the
  empty directories like forensic evidence.
- Six real bugs surfaced *just from reading*: middleware that wiped Redis sessions on
  every request, model adapters that never registered, a dead trace-propagation import,
  an alembic setup that could not migrate a fresh database, four failing tests, and a
  dependency spec (`a2a-sdk>=0.3.25`) that resolved to an incompatible major version on
  any fresh install.

All fixed, all committed. The empty tombstones were deleted.

## Chapter 3: Consolidation (July 4, morning)

The six-repo boundary turned out to be fiction: every Dockerfile required the *parent*
directory as its build context to copy `nexus-common`, which itself had no history.
The repos were merged into one monorepo with `git filter-repo`, preserving every
commit — each service's history is still browsable with `git log -- <service>/`. The
shared library got version control for the first time in its life.

## Chapter 4: The improvement round

With a stable base, one long push added what the lab's purpose demanded: an
`X-Trace-Id` header on every answer flowing into per-message Grafana Tempo links;
reviewer-critic enforcement extended from the CLI to the HTTP path; **dynamic A2A
discovery** (agents registered from whatever their agent cards declare — the weather
agent names *itself*); onboarding (`.env.example`, `make doctor`, `make demo`); a
path-filtered CI workflow, written dormant because no remote existed yet; a uv
workspace replacing three hand-rolled venvs; and a `make new-agent` scaffold that turns
"add an agent" into a two-minute operation ending with one line appended to
`A2A_AGENT_URLS`.

## Chapter 5: First contact with reality (July 4, evening)

Then the stack was actually booted — and containers found what no mocked test could:

- The `cryptography` wheel died with **SIGILL**: the virtualized ARM CPU advertised
  crypto instructions it couldn't execute (`OPENSSL_armcap=0` is in the compose file
  with a comment telling this story).
- `sqlalchemy` was imported directly but had only ever arrived transitively through an
  older `google-adk` — the new version dropped it, breaking *only* fresh containers.
- The dev machine's ports 8080 and 5173 were already taken, and the VM port-forward
  **failed silently** while healthchecks stayed green.

And then the demo ran, and every answer came back as a critique: *"REVISION. The
response is repetitive…"* The reviewer worked — but clients treat the last streamed
event as *the* answer, the draft buffer was double-counting streaming events, and
review turns were polluting persistent chat history. Streaming + review is an ordering
problem; the fix (review out-of-band, in an isolated session, one revision cycle,
verdict as metadata) is one of the most instructive pieces of code in the repo.

## Chapter 6: The incident

With everything green, a human asked the chat two innocent questions — about the
engineering department, then *"What's the weather like?"* — and received a confident
forecast for **"the engineering department"** (partly cloudy, 81°F), followed by a
mysterious extra message walking it back.

The forensics, straight from the Redis session dump: the framework deliberately splices
prior conversation into delegated requests; the weather agent's naive extraction seized
the HR phrase as a city; and wttr.in cheerfully geocodes almost any string. The
reviewer caught the bad draft and its revision cycle produced the "extra" corrective
message — the critic pattern earning its keep in production, live, in front of the one
user. The permanent fixes: sub-agents validate their inputs and refuse to guess, and
the lab's standing rule was written down — **delegated input contains someone else's
conversation.**

## Chapter 7: Publish day (July 5)

Before going public: a secrets audit across every commit of every merged history
(clean — the API key never touched git), home paths scrubbed, a hand-authored SVG mark
(the letter N as a network graph, hub at the crossing), and this README.

Then the last twist, delivered by the very first CI run on real infrastructure: the
Semgrep rule enforcing the project's signature standard — an `EDUCATIONAL NOTE` in
every file — **had never actually run**. Its zero-width regex was dropped by older
engines and misfired on newer ones. The standard was an aspiration the whole time. The
rule was rewritten to genuinely work, promptly found the 19 files that had never been
documented, and every one received a real note. The lab's flagship claim became true
only by being published.

## Epilogue: the meta-lesson

Most of the work described from Chapter 2 onward was performed by AI agents — a
coordinating agent orchestrating fleets of sub-agents that read, verified, fixed,
tested, and documented (the commit trailers say so plainly). A lab about agent
delegation was repaired *by* agent delegation, and the repairing agents hit the same
failure modes the lab teaches: stale context, drifted documentation, over-trusting
input, silent scope boundaries. Their mishaps became the curriculum; the `AGENTS.md`
files at every level are the system documenting itself for the next agent that lands.

The journey isn't over. The discovery story stops at boot time — a running system still
can't notice a new agent joining — and the sticky-vs-hub routing question deserves to
be settled by evals rather than opinion. Those are the next chapters, waiting.
