# Nexus Stack Deployment & Release Procedure

This document outlines the standard procedure for coordinating releases across the Nexus microservice ecosystem.

## 🚀 The Release Lifecycle

In a distributed polyrepo architecture, we separate **Continuous Integration (CI)** from **Continuous Delivery (CD)** to ensure autonomy and safety.

### 1. Service-Level CI (Independent)
Each repository (`nexus-orchestrator`, `nexus-ui`, etc.) is responsible for its own internal quality:
- **Linting & Typing:** Every PR triggers `ruff`, `mypy`, or `eslint`.
- **Unit & Integration Tests:** Automated tests must pass within the service container.
- **Contract Verification:** If the service provides an API, it verifies that its changes don't break the published contract (e.g., OpenAPI or A2A Agent Card).
- **Artifact Creation:** Successful merges to `main` trigger the build of a versioned Docker image (e.g., `nexus-orchestrator:1.2.3`), which is pushed to a private registry.

### 2. Stack-Level Coordination (The Orchestrator)
The `nexus-stack` repository (this repo) acts as the **source of truth** for the environment's state:
- **Environment Promotion:** To "release" a new version, a PR is opened in `nexus-stack` to update the image tags in `docker-compose.yml` or a Helm/Terraform configuration.
- **End-to-End (E2E) Validation:** Before the PR is merged, the `nexus-stack` CI runner spins up the *entire* stack using the new image versions and runs the `nexus-integration` suite.
- **Atomic Deployment:** Once validated, the orchestrator triggers the deployment to the target environment (Dev, Staging, or Production).

---

## 🧪 Local Verification

While production uses automated pipelines, you can simulate these checks locally across all sibling repositories using industry-standard tools.

### The Nexus Verification Stack
We use **Semgrep** for custom architectural rules (like educational notes) and **Checkov** for production-readiness checks (Docker security, multi-stage builds).

#### Prerequisites:
- **Docker**: The verification tools run in their official containers to ensure portability and zero-install setup.
- **Repository Layout**: Sibling repos should be in the same parent directory as `nexus-stack`.

#### Running the Verification:
Run the following command from this directory:
```bash
make verify-all
```

#### What it checks:
1.  **Architectural Integrity (Semgrep)**: Scans every file for `# EDUCATIONAL NOTE:` tags and alerts on their absence.
2.  **Test Isolation (Semgrep)**: Scans for hardcoded external URLs in tests that should be mocked.
3.  **Production Readiness (Checkov)**:
    -   **Multi-stage Builds**: Ensures production images are kept lean.
    -   **Non-root Execution**: Verifies that containers run with a non-root user for security.

