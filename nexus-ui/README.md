# Multi-Agent Orchestrator Frontend

This project is a React-based interactive dashboard built with TypeScript and Vite. It provides a real-time chat interface to interact with a distributed multi-agent system powered by the Google Agent Development Kit (ADK) and Model Context Protocol (MCP).

## 🚀 Getting Started

### Running with Vite (Development)

1.  **Install dependencies**:
    ```bash
    npm install
    ```

2.  **Set environment variables**:
    Create a `.env` file or export the following variable:
    ```bash
    VITE_API_BASE_URL=http://localhost:8080
    ```

3.  **Start the development server**:
    ```bash
    npm run dev
    ```
    The app will be available at `http://localhost:5173`.

### Running with Docker

1.  **Build the image**:
    ```bash
    docker build -t agent-frontend .
    ```

2.  **Run the container**:
    ```bash
    docker run -p 80:80 agent-frontend
    ```
    The app will be served via Nginx at `http://localhost`.

---

## 🧠 Key Logic: HOW & WHY

The frontend is designed to handle asynchronous, streaming communication from multiple backend agents. Below is the documentation for the core architectural patterns used.

### 📡 Server-Sent Events (SSE) Parsing
**Location:** `src/App.tsx` -> `handleSend`

*   **HOW:** We use the native Web Streams API (`response.body.getReader()`) and a `TextDecoder` to process the response stream. We split the incoming chunks by the newline character (`\n`) and filter for lines starting with the `data: ` prefix.
*   **WHY:** The Orchestrator backend emits events using the SSE protocol. Traditional JSON polling or waiting for a full HTTP response would result in a "stuttery" user experience. By parsing the stream in real-time, we can render the agent's thoughts and responses as they are generated.

### 🌊 Delta Accumulation
**Location:** `src/App.tsx` -> `handleSend`

*   **HOW:** The SSE payload includes a `partial` boolean.
    - If `data.partial === true`: We append the new text to a local `accumulatedText` buffer.
    - If `data.partial === false`: We replace the buffer with the final, authoritative text provided in the event.
*   **WHY:** Large Language Models (LLMs) emit "deltas" (small fragments of text). However, network jitter or internal retries can occasionally cause duplicate or missing chunks. The final event (where `partial` is `false`) represents the Orchestrator's verified final state for that message. Replacing the deltas with this final string ensures the UI is perfectly synced with the backend.

### 🤝 Delegation Tracking
**Location:** `src/App.tsx` -> `handleSend`

*   **HOW:** We maintain an `announcedDelegation` string in the local scope of the `handleSend` function. When an event contains a `transferToAgent` action, we check if the target agent name differs from the current `announcedDelegation`. If it does, we push a system message to the chat and update the tracker.
*   **WHY:** During a handoff between agents (e.g., Root -> HR Agent), the ADK might emit multiple transfer events as the orchestrator stabilizes the connection. Without tracking, the UI would display redundant "Delegating to..." messages. This logic ensures the user sees a single, clean notification for each agent switch.

---

## 🛠️ Tech Stack

- **React 19**: UI Library.
- **TypeScript**: Type safety.
- **Vite**: Fast build tool and dev server.
- **Tailwind CSS**: Utility-first styling with typography support for Markdown.
- **React Markdown**: Safe rendering of agent-generated Markdown.
- **Nginx**: Production-grade static file serving via Docker.


## 📏 Nexus Engineering Standards

This project adheres to the **Nexus Engineering Standards**, prioritizing educational clarity, production-grade quality, and architectural consistency. All contributors and sub-agents must follow these mandates:

### 1. Educational Integrity
- **Prefix:** Standardize all architectural and 'Why' commentary using the `# EDUCATIONAL NOTE:` (or language-appropriate) prefix.
- **Clarity:** Every non-trivial architectural choice must be accompanied by a note explaining the trade-offs and rationale.

### 2. Code Quality & Type Safety
- **Python:** Strict linting via `ruff` and static type checking via `mypy`.
- **UI/TypeScript:** Enforce `strict: true` in `tsconfig.json` and use ESLint for React/TypeScript best practices.
- **Automation:** Quality checks should be integrated into the `Makefile` or CI/CD pipelines.

### 3. Testing Isolation
- **No Side Effects:** Tests must be completely isolated. They must never hit external APIs (Gemini, Open-Meteo, etc.) or production resources.
- **Mocking:** Use robust mocking (e.g., `unittest.mock`, `pytest-mock`, `MSW`) to simulate all external dependencies and network boundaries.

### 4. Containerization & Production Readiness
- **Multi-stage Builds:** Dockerfiles must use multi-stage builds to keep production images lean.
- **Security:** Always run containers as a non-root user (`USER appuser`).
- **Healthchecks:** Every service must define a native `HEALTHCHECK` in its Dockerfile and/or `docker-compose.yml`.

### 5. Documentation
- **Living Reference:** `GEMINI.md` and `README.md` must be kept in sync with the project's actual state.
- **Architectural Diagrams:** Use Mermaid.js or clear text-based diagrams to visualize service interactions.
