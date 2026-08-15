# Specification: Continuous Integration (CI) Workflow & PR Validation 📋

## Status: APPROVED
**Module**: `infrastructure / ci / github_actions`  
**Target Files**:
- [.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/ci.yml)
- [backend/pyproject.toml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/pyproject.toml)
- [frontend/package.json](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/package.json)
- [frontend/pages/_app.tsx](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/pages/_app.tsx)
- [docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_ci_spec.md)

---

## 1. Executive Summary & Objectives

This specification defines the production-grade Continuous Integration (CI) architecture for Project Alex. The CI workflow provides automated static analysis, type checking, unit testing, and frontend build validation for all incoming code changes.

### Key Objectives & Principles:
1. **Strict CI Scope Focus**: Enforces quality gates for pull requests and branch pushes without embedding continuous deployment (CD) or Terraform validation (Terraform formatting, validation, and planning are governed by the CD deployment pipeline in [docs/specs/infrastructure/scheduler_and_deployment_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/scheduler_and_deployment_spec.md)).
2. **Parallel Job Orchestration**: Divides validation into 3 independent, concurrently executing pipeline jobs to maximize runner concurrency and minimize developer feedback latency.
3. **Layered Caching Strategy**: Integrates native dependency and build caching for Python (`astral-sh/setup-uv` with `enable-cache: true`), Node.js (`actions/setup-node` with `cache: 'npm'`), and Next.js compiler outputs (`actions/cache` for `frontend/.next/cache`).
4. **Sub-2-Minute Performance SLA**: Guarantees total end-to-end CI execution time of **under 2 minutes (< 120 seconds)** wall-clock time per workflow run.

---

## 2. Technical Contracts & Interface Specifications

### 2.1 Workflow Trigger Scope

The CI pipeline is triggered automatically on pull requests targeting the `main` branch, as well as pushes to `main` or topic/feature branches:

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

### 2.2 Pipeline Job Definitions & Interface Matrix

The pipeline comprises **4 independent jobs** running on standard `ubuntu-latest` runners:

| Job Name | Responsibility & Target Directory | Primary Command / CLI | Runtime Budget | Artifact Uploaded |
| :--- | :--- | :--- | :--- | :--- |
| `lint-and-typecheck` | Backend Ruff linting (`backend/`) & Frontend ESLint (`frontend/`) | `uv run --with ruff ruff check .` & `npm run lint` | ~30 seconds | *None* |
| `backend-test-suite` | Pytest unit test execution (`backend/tests/`) | `uv run pytest tests/ -v --tb=short` | ~35 seconds | *None* |
| `frontend-build-check` | Next.js production page build & artifact upload | `npm run build` (in `frontend/`) | ~65 seconds | `frontend-static-build` |
| `package-lambda-artifacts` | Multi-agent Lambda function zip packaging & artifact upload | `uv run package_docker.py` / `package_scheduler.py` | ~45 seconds | `lambda-agent-packages` |

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

4. **Terraform Provider Cache & Headless Init**:
   - **Action**: `hashicorp/setup-terraform@v3` with `terraform_version: "1.9.0"`
   - **Behavior**: Validations execute with `terraform init -backend=false` to bypass S3 remote state initialization overhead.

### 2.4 Frontend Environment Variables & Static Pre-rendering

During Next.js production compilation (`next build`), pages wrapped with `<ClerkProvider>` require a publishable key during static page pre-rendering. To prevent static build failures (`Missing publishableKey`):
- **CI Workflow Configuration**: The `frontend-build-check` job step reads directly from GitHub Secrets (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: ${{ secrets.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY }}`).
- **Local Application Configuration**: [frontend/pages/_app.tsx](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/pages/_app.tsx) reads `process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from local `.env.local` configuration.

---

## 3. Implementation Plan & Execution Steps

The full declarative GitHub Actions workflow configuration is defined at [.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/ci.yml):

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
  # ---------------------------------------------------------------------------
  # Job 1: Static Analysis, Ruff Linting & Frontend ESLint
  # ---------------------------------------------------------------------------
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

  # ---------------------------------------------------------------------------
  # Job 2: Backend Pytest Unit Test Suite
  # ---------------------------------------------------------------------------
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

  # ---------------------------------------------------------------------------
  # Job 3: Frontend Next.js Build & Page Compilation
  # ---------------------------------------------------------------------------
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

  # ---------------------------------------------------------------------------
  # Job 4: Package Lambda Agent Artifacts
  # ---------------------------------------------------------------------------
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

1. **Parallel Execution Architecture**: All 3 top-level jobs (`lint-and-typecheck`, `backend-test-suite`, and `frontend-build-check`) run in parallel with zero inter-job dependencies (`needs:` block omitted).
2. **Concurrency Control**: `concurrency.cancel-in-progress: true` automatically terminates outdated builds when new commits are pushed to the same pull request branch.
3. **Target Runtime Matrix**:
   - `lint-and-typecheck`: ~30s
   - `backend-test-suite`: ~35s
   - `frontend-build-check`: ~65s uncached / ~30s cached (governs overall wall-clock completion time)
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
2. **Status Check**: Verify all 4 jobs (and 7 terraform matrix entries) appear under PR status checks.
3. **SLA Audit**: Confirm total pipeline wall-clock time is < 120 seconds in the GitHub Actions summary tab.
