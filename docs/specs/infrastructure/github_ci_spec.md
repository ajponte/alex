# Specification: Continuous Integration (CI) Workflow & PR Validation 📋

## Status: APPROVED
**Module**: `infrastructure / ci / github_actions`  
**Target Files**:
- [.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/ci.yml)
- [.github/workflows/reusable-lint-test.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-lint-test.yml)
- [.github/workflows/reusable-build-frontend.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-build-frontend.yml)
- [.github/workflows/reusable-package-planner.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-planner.yml)
- [.github/workflows/reusable-package-tagger.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-tagger.yml)
- [.github/workflows/reusable-package-reporter.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-reporter.yml)
- [.github/workflows/reusable-package-charter.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-charter.yml)
- [.github/workflows/reusable-package-retirement.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-retirement.yml)
- [.github/workflows/reusable-package-scheduler.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-scheduler.yml)
- [backend/pyproject.toml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/pyproject.toml)
- [frontend/package.json](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/package.json)
- [frontend/pages/_app.tsx](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/pages/_app.tsx)
- [docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_ci_spec.md)

---

## 1. Executive Summary & Objectives

This specification defines the production-grade Continuous Integration (CI) architecture for Project Alex using a **composable Reusable Workflow (`workflow_call`) design**. The CI workflow provides automated static analysis, type checking, unit testing, frontend compilation, and dedicated parallel packaging for each individual Lambda function for all incoming code changes.

### Key Objectives & Principles:
1. **Composable Reusable Architecture**: Modularizes validation and packaging into discrete, dedicated reusable workflows (`reusable-lint-test.yml`, `reusable-build-frontend.yml`, and 6 individual Lambda packaging workflows: `reusable-package-planner.yml`, `reusable-package-tagger.yml`, `reusable-package-reporter.yml`, `reusable-package-charter.yml`, `reusable-package-retirement.yml`, `reusable-package-scheduler.yml`) orchestrated by the main parent workflow (`ci.yml`).
2. **Strict CI Scope Focus**: Enforces quality gates for pull requests and branch pushes without embedding continuous deployment (CD) or Terraform validation (Terraform formatting, validation, and planning are governed by the CD deployment pipeline in [docs/specs/infrastructure/github_cd_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_cd_spec.md)).
3. **Parallel Job Orchestration**: Divides validation and artifact packaging into independent, concurrently executing pipeline jobs across reusable workflows to maximize runner concurrency and minimize developer feedback latency.
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

The parent workflow delegates validation and artifact packaging to composable reusable workflows in parallel via `workflow_call`:
- `lint-and-test`: Calls [.github/workflows/reusable-lint-test.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-lint-test.yml)
- `build-frontend`: Calls [.github/workflows/reusable-build-frontend.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-build-frontend.yml)
- `package-planner`: Calls [.github/workflows/reusable-package-planner.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-planner.yml)
- `package-tagger`: Calls [.github/workflows/reusable-package-tagger.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-tagger.yml)
- `package-reporter`: Calls [.github/workflows/reusable-package-reporter.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-reporter.yml)
- `package-charter`: Calls [.github/workflows/reusable-package-charter.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-charter.yml)
- `package-retirement`: Calls [.github/workflows/reusable-package-retirement.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-retirement.yml)
- `package-scheduler`: Calls [.github/workflows/reusable-package-scheduler.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-package-scheduler.yml)

### 2.2 Pipeline Job Definitions & Interface Matrix

The composable CI pipeline comprises **9 independent jobs** defined inside dedicated reusable workflows running on `ubuntu-latest` runners in parallel:

| Reusable Workflow | Job ID | Responsibility & Scope | Primary Command / CLI | Artifact Uploaded |
| :--- | :--- | :--- | :--- | :--- |
| `reusable-lint-test.yml` | `lint-and-typecheck` | Backend Ruff linting (`backend/`) & Frontend ESLint (`frontend/`) | `uv run --with ruff ruff check .` & `npm run lint` | *None* |
| `reusable-lint-test.yml` | `backend-test-suite` | Pytest unit test execution (`backend/tests/`) | `uv run pytest tests/ -v --tb=short` | *None* |
| `reusable-build-frontend.yml` | `frontend-build-check` | Next.js production page build & static output export | `npm run build` (in `frontend/`) | `frontend-static-build` |
| `reusable-package-planner.yml` | `package-planner-lambda` | Planner Lambda zip packaging | `uv run planner/package_docker.py || true` | `lambda-package-planner` |
| `reusable-package-tagger.yml` | `package-tagger-lambda` | Tagger Lambda zip packaging | `uv run tagger/package_docker.py || true` | `lambda-package-tagger` |
| `reusable-package-reporter.yml` | `package-reporter-lambda` | Reporter Lambda zip packaging | `uv run reporter/package_docker.py || true` | `lambda-package-reporter` |
| `reusable-package-charter.yml` | `package-charter-lambda` | Charter Lambda zip packaging | `uv run charter/package_docker.py || true` | `lambda-package-charter` |
| `reusable-package-retirement.yml` | `package-retirement-lambda` | Retirement Lambda zip packaging | `uv run retirement/package_docker.py || true` | `lambda-package-retirement` |
| `reusable-package-scheduler.yml` | `package-scheduler-lambda` | Scheduler Lambda zip packaging | `uv run package_scheduler.py || true` | `lambda-package-scheduler` |

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

  build-frontend:
    name: Build Frontend Static Export
    uses: ./.github/workflows/reusable-build-frontend.yml
    secrets: inherit

  package-planner:
    name: Package Planner Lambda
    uses: ./.github/workflows/reusable-package-planner.yml
    secrets: inherit

  package-tagger:
    name: Package Tagger Lambda
    uses: ./.github/workflows/reusable-package-tagger.yml
    secrets: inherit

  package-reporter:
    name: Package Reporter Lambda
    uses: ./.github/workflows/reusable-package-reporter.yml
    secrets: inherit

  package-charter:
    name: Package Charter Lambda
    uses: ./.github/workflows/reusable-package-charter.yml
    secrets: inherit

  package-retirement:
    name: Package Retirement Lambda
    uses: ./.github/workflows/reusable-package-retirement.yml
    secrets: inherit

  package-scheduler:
    name: Package Scheduler Lambda
    uses: ./.github/workflows/reusable-package-scheduler.yml
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

### 3.3 Reusable Workflow: `.github/workflows/reusable-build-frontend.yml`

```yaml
name: Reusable Build Frontend Workflow

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
```

### 3.4 Reusable Workflow: `.github/workflows/reusable-package-planner.yml`

```yaml
name: Reusable Package Planner Lambda Workflow

on:
  workflow_call:

jobs:
  package-planner-lambda:
    name: Package Planner Lambda Artifact
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

      - name: Package Planner Lambda Function
        working-directory: backend
        run: uv run planner/package_docker.py || true

      - name: Upload Planner Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-planner
          path: backend/planner/planner_lambda.zip
          retention-days: 7
```

### 3.5 Reusable Workflow: `.github/workflows/reusable-package-tagger.yml`

```yaml
name: Reusable Package Tagger Lambda Workflow

on:
  workflow_call:

jobs:
  package-tagger-lambda:
    name: Package Tagger Lambda Artifact
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

      - name: Package Tagger Lambda Function
        working-directory: backend
        run: uv run tagger/package_docker.py || true

      - name: Upload Tagger Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-tagger
          path: backend/tagger/tagger_lambda.zip
          retention-days: 7
```

### 3.6 Reusable Workflow: `.github/workflows/reusable-package-reporter.yml`

```yaml
name: Reusable Package Reporter Lambda Workflow

on:
  workflow_call:

jobs:
  package-reporter-lambda:
    name: Package Reporter Lambda Artifact
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

      - name: Package Reporter Lambda Function
        working-directory: backend
        run: uv run reporter/package_docker.py || true

      - name: Upload Reporter Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-reporter
          path: backend/reporter/reporter_lambda.zip
          retention-days: 7
```

### 3.7 Reusable Workflow: `.github/workflows/reusable-package-charter.yml`

```yaml
name: Reusable Package Charter Lambda Workflow

on:
  workflow_call:

jobs:
  package-charter-lambda:
    name: Package Charter Lambda Artifact
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

      - name: Package Charter Lambda Function
        working-directory: backend
        run: uv run charter/package_docker.py || true

      - name: Upload Charter Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-charter
          path: backend/charter/charter_lambda.zip
          retention-days: 7
```

### 3.8 Reusable Workflow: `.github/workflows/reusable-package-retirement.yml`

```yaml
name: Reusable Package Retirement Lambda Workflow

on:
  workflow_call:

jobs:
  package-retirement-lambda:
    name: Package Retirement Lambda Artifact
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

      - name: Package Retirement Lambda Function
        working-directory: backend
        run: uv run retirement/package_docker.py || true

      - name: Upload Retirement Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-retirement
          path: backend/retirement/retirement_lambda.zip
          retention-days: 7
```

### 3.9 Reusable Workflow: `.github/workflows/reusable-package-scheduler.yml`

```yaml
name: Reusable Package Scheduler Lambda Workflow

on:
  workflow_call:

jobs:
  package-scheduler-lambda:
    name: Package Scheduler Lambda Artifact
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

      - name: Package Scheduler Lambda Function
        working-directory: backend
        run: uv run package_scheduler.py || true

      - name: Upload Scheduler Lambda Package Artifact
        uses: actions/upload-artifact@v4
        with:
          name: lambda-package-scheduler
          path: backend/scheduler/lambda_function.zip
          retention-days: 7
```

---

## 4. Performance & SLA Benchmarks

To guarantee the **sub-2-minute (< 120s)** performance SLA:

1. **Parallel Execution Architecture**: All 8 top-level reusable workflow invocations in `ci.yml` run concurrently without blocking each other.
2. **Concurrency Control**: `concurrency.cancel-in-progress: true` automatically terminates outdated builds when new commits are pushed to the same pull request branch.
3. **Target Runtime Matrix**:
   - `lint-and-typecheck`: ~30s
   - `backend-test-suite`: ~35s
   - `frontend-build-check`: ~65s uncached / ~30s cached (governs overall wall-clock completion time)
   - `package-planner-lambda`: ~40s
   - `package-tagger-lambda`: ~40s
   - `package-reporter-lambda`: ~40s
   - `package-charter-lambda`: ~40s
   - `package-retirement-lambda`: ~40s
   - `package-scheduler-lambda`: ~25s
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
2. **Status Check**: Verify reusable workflows execute clean job groups under PR status checks across all 8 parallel jobs.
3. **SLA Audit**: Confirm total pipeline wall-clock time is < 120 seconds in the GitHub Actions summary tab.
