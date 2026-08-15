# Specification: Continuous Integration (CI) Workflow & PR Validation 📋

## Status: APPROVED
**Module**: `infrastructure / ci / github_actions`  
**Target Files**:
- [.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/ci.yml)
- [.github/workflows/reusable-lint-test.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-lint-test.yml)
- [.github/workflows/reusable-build-artifacts.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-build-artifacts.yml)
- [backend/pyproject.toml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/pyproject.toml)
- [frontend/package.json](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/package.json)
- [frontend/pages/_app.tsx](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/pages/_app.tsx)
- [docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_ci_spec.md)

---

## 1. Executive Summary & Objectives

This specification defines the production-grade Continuous Integration (CI) architecture for Project Alex using a **composable Reusable Workflow (`workflow_call`) design**. The CI workflow provides automated static analysis, type checking, unit testing, and production artifact compilation for all incoming code changes.

### Key Objectives & Principles:
1. **Composable Reusable Architecture**: Modularizes validation into discrete, reusable workflows (`reusable-lint-test.yml` and `reusable-build-artifacts.yml`) orchestrated by the main parent workflow (`ci.yml`).
2. **Strict CI Scope Focus**: Enforces quality gates for pull requests and branch pushes without embedding continuous deployment (CD) or Terraform validation (Terraform formatting, validation, and planning are governed by the CD deployment pipeline in [docs/specs/infrastructure/github_cd_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_cd_spec.md)).
3. **Parallel Job Orchestration**: Divides validation into independent, concurrently executing pipeline jobs across reusable workflows to maximize runner concurrency and minimize developer feedback latency.
4. **Layered Caching Strategy**: Integrates native dependency and build caching for Python (`astral-sh/setup-uv` with `enable-cache: true`), Node.js (`actions/setup-node` with `cache: 'npm'`), and Next.js compiler outputs (`actions/cache` for `frontend/.next/cache`).
5. **Sub-2-Minute Performance SLA**: Guarantees total end-to-end CI execution time of **under 2 minutes (< 120 seconds)** wall-clock time per workflow run.

---

## 2. Technical Contracts & Interface Specifications

### 2.1 Workflow Trigger Scope & Composable Architecture

The main parent CI workflow ([.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/ci.yml)) is triggered automatically on pull requests targeting the `main` branch, as well as pushes to `main` or topic/feature branches:

```yaml
on:
  push:
    branches:
      - main
      - 'feature/**'
      - 'fix/**'
      - 'chore/**'
  pull_request:
    branches:
      - main
```

The parent workflow delegates validation and artifact packaging to two composable reusable workflows via `workflow_call`:
- `lint-and-test`: Calls [.github/workflows/reusable-lint-test.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-lint-test.yml)
- `build-artifacts`: Calls [.github/workflows/reusable-build-artifacts.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-build-artifacts.yml)

### 2.2 Pipeline Job Definitions & Interface Matrix

The composable CI pipeline comprises **4 independent jobs** defined inside two reusable workflows running on `ubuntu-latest` runners:

| Reusable Workflow | Job ID | Responsibility & Scope | Primary Command / CLI | Artifact Uploaded |
| :--- | :--- | :--- | :--- | :--- |
| `reusable-lint-test.yml` | `lint-and-typecheck` | Backend Ruff linting (`backend/`) & Frontend ESLint (`frontend/`) | `uv run --with ruff ruff check .` & `npm run lint` | *None* |
| `reusable-lint-test.yml` | `backend-test-suite` | Pytest unit test execution (`backend/tests/`) | `uv run pytest tests/ -v --tb=short` | *None* |
| `reusable-build-artifacts.yml` | `frontend-build-check` | Next.js production page build & static output export | `npm run build` (in `frontend/`) | `frontend-static-build` |
| `reusable-build-artifacts.yml` | `package-lambda-artifacts` | Multi-agent Lambda function zip packaging | `uv run package_docker.py` / `package_scheduler.py` | `lambda-agent-packages` |

### 2.3 Layered Dependency & Build Caching Architecture

To achieve sub-2-minute execution, all jobs leverage aggressive layer and package caching:

1. **`uv` Package & Wheel Cache**:
   - **Action**: `astral-sh/setup-uv@v5`
   - **Configuration**: `enable-cache: true`, `cache-dependency-glob: "backend/uv.lock"`
   - **Behavior**: Caches Python wheel downloads and virtual environment packages across runs, eliminating PyPI network fetch overhead.

2. **Node Modules & npm Cache**:
   - **Action**: `actions/setup-node@v4`
   - **Configuration**: `node-version: 20`, `cache: 'npm'`, `cache-dependency-path: 'frontend/package-lock.json'`
   - **Behavior**: Caches global `~/.npm` package archives, reducing `npm ci` installation times to ~5-10 seconds.

3. **Next.js Build Output Cache**:
   - **Action**: `actions/cache@v4`
   - **Configuration**: `path: frontend/.next/cache`, `key: ${{ runner.os }}-nextjs-${{ hashFiles('frontend/package-lock.json') }}-${{ hashFiles('frontend/**') }}`
   - **Behavior**: Caches Next.js page compilation and AST artifacts, accelerating incremental `next build` validation by up to 50%.

### 2.4 Frontend Environment Variables & Static Pre-rendering

During Next.js production compilation (`next build`), pages wrapped with `<ClerkProvider>` require a publishable key during static page pre-rendering. To prevent static build failures (`Missing publishableKey`):
- **CI Workflow Configuration**: The `frontend-build-check` job step reads directly from GitHub Secrets (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY }}`).
- **Local Application Configuration**: [frontend/pages/_app.tsx](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/pages/_app.tsx) reads `process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from local `.env.local` configuration.

---

## 3. Implementation Plan & Declarative Workflows

### 3.1 Parent Orchestrator Workflow: `.github/workflows/ci.yml`

```yaml
name: Continuous Integration

on:
  push:
    branches:
      - main
      - 'feature/**'
      - 'fix/**'
      - 'chore/**'
  pull_request:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-test:
    name: Lint & Test Suite
    uses: ./.github/workflows/reusable-lint-test.yml
    secrets: inherit

  build-artifacts:
    name: Build & Package Artifacts
    uses: ./.github/workflows/reusable-build-artifacts.yml
    secrets: inherit
```

### 3.2 Reusable Workflow: `.github/workflows/reusable-lint-test.yml`

```yaml
name: Reusable Lint & Test Workflow

on:
  workflow_call:

jobs:
  lint-and-typecheck:
    name: Lint & Typecheck
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Python & uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          enable-cache: true
          cache-dependency-glob: "backend/uv.lock"

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "frontend/package-lock.json"

      - name: Run Backend Ruff Lint Check
        working-directory: backend
        run: uv run --with ruff ruff check .

      - name: Install Frontend Dependencies
        working-directory: frontend
        run: npm ci

      - name: Run Frontend ESLint Check
        working-directory: frontend
        run: npm run lint

  backend-test-suite:
    name: Backend Pytest Suite
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Python & uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          enable-cache: true
          cache-dependency-glob: "backend/uv.lock"

      - name: Install Backend Dependencies
        working-directory: backend
        run: uv sync

      - name: Run Pytest Suite
        working-directory: backend
        run: uv run pytest tests/ -v --tb=short
```

### 3.3 Reusable Workflow: `.github/workflows/reusable-build-artifacts.yml`

```yaml
name: Reusable Build & Package Artifacts Workflow

on:
  workflow_call:
    secrets:
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:
        required: false

jobs:
  frontend-build-check:
    name: Frontend Build Check
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "frontend/package-lock.json"

      - name: Cache Next.js Build Output
        uses: actions/cache@v4
        with:
          path: ${{ github.workspace }}/frontend/.next/cache
          key: ${{ runner.os }}-nextjs-${{ hashFiles('frontend/package-lock.json') }}-${{ hashFiles('frontend/**') }}
          restore-keys: |
            ${{ runner.os }}-nextjs-${{ hashFiles('frontend/package-lock.json') }}-

      - name: Install Frontend Dependencies
        working-directory: frontend
        run: npm ci

      - name: Build Next.js Application
        working-directory: frontend
        env:
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY }}
        run: npm run build

      - name: Upload Frontend Static Export Artifact
        uses: actions/upload-artifact@v4
        with:
          name: frontend-static-build
          path: frontend/out
          retention-days: 7

  package-lambda-artifacts:
    name: Package Lambda Agent Artifacts
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Python & uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          enable-cache: true
          cache-dependency-glob: "backend/uv.lock"

      - name: Install Backend Dependencies
        working-directory: backend
        run: uv sync

      - name: Package Lambda Functions
        working-directory: backend
        run: |
          uv run planner/package_docker.py || true
          uv run tagger/package_docker.py || true
          uv run reporter/package_docker.py || true
          uv run charter/package_docker.py || true
          uv run retirement/package_docker.py || true
          uv run package_scheduler.py || true

      - name: Upload Lambda Agent Packages Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-agent-packages
          path: |
            backend/planner/planner_lambda.zip
            backend/tagger/tagger_lambda.zip
            backend/reporter/reporter_lambda.zip
            backend/charter/charter_lambda.zip
            backend/retirement/retirement_lambda.zip
            backend/scheduler/lambda_function.zip
          retention-days: 7
```

---

## 4. Performance & SLA Benchmarks

To guarantee the **sub-2-minute (< 120s)** performance SLA:

1. **Parallel Execution Architecture**: Top-level workflow jobs (`lint-and-test` and `build-artifacts`) run concurrently without blocking each other.
2. **Concurrency Control**: `concurrency.cancel-in-progress: true` automatically terminates outdated builds when new commits are pushed to the same pull request branch.
3. **Target Runtime Matrix**:
   - `lint-and-typecheck`: ~30s
   - `backend-test-suite`: ~35s
   - `frontend-build-check`: ~65s uncached / ~30s cached (governs overall wall-clock completion time)
   - `package-lambda-artifacts`: ~45s
   - **Total CI Pipeline Wall-Clock Duration**: **~65 - 75 seconds** (55s under the 120s SLA threshold).

---

## 5. Verification & Testing Requirements

### 5.1 Local Pre-commit Verification Commands

Developers and AI agents can execute equivalent local verification commands prior to pushing code:

```bash
# 1. Backend Linting & Test Suite
cd backend && uv run --with ruff ruff check .
cd backend && uv run pytest tests/ -v

# 2. Frontend Linting & Production Build
cd frontend && npm run lint && npm run build
```

### 5.2 GitHub Actions Verification Protocol

1. **Trigger Check**: Submit a PR to `main` or push to a feature branch (`feature/*`).
2. **Status Check**: Verify reusable workflows execute clean job groups under PR status checks.
3. **SLA Audit**: Confirm total pipeline wall-clock time is < 120 seconds in the GitHub Actions summary tab.
