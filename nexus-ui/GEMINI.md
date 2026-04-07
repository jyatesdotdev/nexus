# GEMINI.md - Multi-Agent Orchestrator Frontend

This project is the interactive dashboard for the Multi-Agent Orchestrator system. It provides a real-time chat interface to interact with a distributed multi-agent system powered by the Google Agent Development Kit (ADK) and Model Context Protocol (MCP).

## 🚀 Project Overview

The frontend is a React-based application built with TypeScript and Vite. It is designed to handle asynchronous, streaming communication from multiple backend agents and provide a real-time view of the system's health.

### Key Technologies
- **Framework:** React 19
- **Build Tool:** Vite
- **Language:** TypeScript
- **Styling:** Tailwind CSS (with Typography plugin for Markdown)
- **Testing:** Vitest, React Testing Library
- **Rendering:** React Markdown (for agent responses)
- **Communication:** Server-Sent Events (SSE) via Web Streams API

## 🏗️ Architecture & Components

The system is structured as a modern React application with a focus on real-time streaming and modular UI components.

1.  **`App.tsx`**: The root component. Manages global state, polling for system status, and the core SSE streaming logic for the chat.
2.  **`components/`**: Contains modular UI components:
    - `MessageList.tsx`: Renders the chat history with support for Markdown and scrolling.
    - `MessageInput.tsx`: Handles user input and submission.
    - `SystemStatusGrid.tsx`: Displays real-time health status of backend services (Orchestrator, MCP Server, A2A Agent).
    - `ui/`: A collection of reusable base components (Button, Card, Input, Badge).
3.  **`lib/utils.ts`**: Utility functions for styling (Tailwind merge and clsx).
4.  **`types.ts`**: Centralized TypeScript interfaces for messages and service statuses.

### Real-Time Logic (HOW & WHY)
- **SSE Parsing:** Uses the native Web Streams API to process incoming chunks of data from the Orchestrator. This prevents "stuttery" UI and allows rendering agent thoughts as they are generated.
- **Delta Accumulation:** LLM deltas are accumulated and replaced by a final authoritative string when the stream completes to ensure UI consistency.
- **Delegation Tracking:** Automatically detects and displays system messages when the orchestrator hands off a task to a specialized sub-agent (e.g., "Delegating to HR Agent...").

## 🛠️ Building and Running

| Task | Command | Description |
| :--- | :--- | :--- |
| **Install** | `npm install` | Installs project dependencies. |
| **Dev** | `npm run dev` | Starts the Vite development server (default: `http://localhost:5173`). |
| **Build** | `npm run build` | Compiles TypeScript and builds the production-ready assets. |
| **Test** | `npm run test` | Runs the test suite using Vitest. |
| **Lint** | `npm run lint` | Runs ESLint for code quality checks. |
| **Preview** | `npm run preview` | Locally previews the production build. |

### Environment Variables
The application uses the following environment variable:
- `VITE_API_BASE_URL`: The base URL of the Orchestrator backend (default: `http://localhost:8080`).

## 📏 Development Conventions

### Coding Standards
- **Functional Components:** Use functional components with hooks (`useState`, `useEffect`, `useRef`).
- **TypeScript:** Strict typing for all components and state objects. Prefer interfaces over types for data structures.
- **Tailwind CSS:** Use utility-first styling. Prefer the `cn()` utility (from `src/lib/utils.ts`) for conditional class merging.
- **Docstrings:** Use JSDoc-style comments for components and complex logic to assist AI agents and developers.

### Testing Practices
- **Component Testing:** Use React Testing Library for behavioral testing of components.
- **Global Setup:** Global test configurations are in `src/setupTests.ts`.
- **Coverage:** Vitest is configured to use `v8` for coverage reporting.

### UI Consistency
- Follow the design patterns established in the `components/ui/` directory.
- Use the `Badge` component for status indicators and `Card` for structural layout.


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
