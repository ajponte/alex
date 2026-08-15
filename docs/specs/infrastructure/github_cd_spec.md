# Specification: Continuous Deployment (CD) Workflow & Production Infrastructure Release 🚀

## Status: APPROVED
**Module**: `infrastructure / cd / github_actions`  
**Target Files**:
- [.github/workflows/cd.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/cd.yml)
- [.github/workflows/reusable-terraform-apply.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-terraform-apply.yml)
- [.github/workflows/reusable-deploy-lambdas.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-deploy-lambdas.yml)
- [.github/workflows/reusable-deploy-frontend.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/reusable-deploy-frontend.yml)
- [backend/deploy_all_lambdas.py](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/deploy_all_lambdas.py)
- [frontend/package.json](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/frontend/package.json)
- [terraform/2_sagemaker/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/2_sagemaker/main.tf)
- [terraform/3_ingestion/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/3_ingestion/main.tf)
- [terraform/4_researcher/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/4_researcher/main.tf)
- [terraform/5_database/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/5_database/main.tf)
- [terraform/6_agents/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/6_agents/main.tf)
- [terraform/7_frontend/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/7_frontend/main.tf)
- [terraform/8_enterprise/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/8_enterprise/main.tf)
- [docs/specs/infrastructure/github_cd_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_cd_spec.md)

---

## 1. Executive Summary & Objectives

This specification defines the production-grade Continuous Deployment (CD) pipeline architecture for Project Alex using a **composable Reusable Workflow (`workflow_call`) design**. The CD workflow orchestrates automated infrastructure provisioning across multi-stack Terraform modules, containerized Lambda agent deployments, Next.js frontend asset delivery to AWS S3, and CloudFront CDN cache invalidations following successful Continuous Integration (CI) runs on the `main` branch or via manual dispatch.

### Key Objectives & Architectural Principles:
1. **Composable Reusable CD Architecture**: Deconstructs production release steps into modular reusable workflows (`reusable-terraform-apply.yml`, `reusable-deploy-lambdas.yml`, and `reusable-deploy-frontend.yml`) invoked by the parent orchestration workflow (`cd.yml`).
2. **Automated Continuous Deployment Trigger Scope**: Automatically triggers deployment following successful completion of the CI workflow ([docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_ci_spec.md)) on `main` via `workflow_run` events, or on-demand via manual `workflow_dispatch`.
3. **Passwordless AWS Authentication (OIDC)**: Integrates GitHub Actions OpenID Connect (OIDC) identity provider federation (`aws-actions/configure-aws-credentials`) using IAM role assumption (`role-to-assume: ${{ secrets.AWS_ROLE_ARN }}`), eliminating long-lived access key secrets.
4. **Terraform Stack Matrix Provisioning**: Executes `terraform fmt -check`, `terraform init`, `terraform validate`, and `terraform apply -auto-approve` sequentially across all active Terraform modules (`2_sagemaker` through `8_enterprise`) inside `reusable-terraform-apply.yml`.
5. **Consuming Pre-Packaged Lambda Artifacts**: Downloads the 6 individual Lambda package artifacts (`lambda-package-planner`, `lambda-package-tagger`, `lambda-package-reporter`, `lambda-package-charter`, `lambda-package-retirement`, `lambda-package-scheduler`) into their respective `backend/` subdirectories and invokes [backend/deploy_all_lambdas.py](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/deploy_all_lambdas.py) **without** the `--package` flag inside `reusable-deploy-lambdas.yml`.
6. **Consuming Pre-Built Frontend Artifacts & CDN Invalidation**: Downloads pre-compiled `frontend-static-build` export artifacts directly into `frontend/out/`, synchronizes static assets to S3 (`aws s3 sync`), and invalidates CloudFront distributions (`aws cloudfront create-invalidation`) inside `reusable-deploy-frontend.yml`.

> [!IMPORTANT]
> Infrastructure deployment safety is governed by non-preemptive concurrency locks (`cancel-in-progress: false`). Ongoing `terraform apply` operations are never aborted mid-execution, protecting state backends against lock corruption.

---

## 2. Technical Contracts & Interface Specifications

### 2.1 Workflow Triggers & Artifact Inheritance Mechanism

The parent CD pipeline ([.github/workflows/cd.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/.github/workflows/cd.yml)) triggers automatically upon successful completion of the Continuous Integration (CI) pipeline on the `main` branch, or via manual dispatch from the GitHub Actions UI:

```yaml
on:
  workflow_run:
    workflows: ["Continuous Integration"]
    types:
      - completed
    branches:
      - main
  workflow_dispatch:
    inputs:
      run_id:
        description: 'CI Workflow Run ID (optional, defaults to triggering/latest CI run)'
        required: false
        type: string
```

#### CI Artifact Inheritance Protocol:
1. **CI Artifact Generation**: The CI workflow ([docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/infrastructure/github_ci_spec.md)) produces 7 validated build artifacts:
   - `frontend-static-build`: Exported static build HTML/JS assets from `frontend/out`.
   - `lambda-package-planner`: Package archive for Planner Lambda (`backend/planner/planner_lambda.zip`).
   - `lambda-package-tagger`: Package archive for Tagger Lambda (`backend/tagger/tagger_lambda.zip`).
   - `lambda-package-reporter`: Package archive for Reporter Lambda (`backend/reporter/reporter_lambda.zip`).
   - `lambda-package-charter`: Package archive for Charter Lambda (`backend/charter/charter_lambda.zip`).
   - `lambda-package-retirement`: Package archive for Retirement Lambda (`backend/retirement/retirement_lambda.zip`).
   - `lambda-package-scheduler`: Package archive for Scheduler Lambda (`backend/scheduler/lambda_function.zip`).
2. **Quality Gate Guardrail**: The CD workflow inspects the CI execution result:
   ```yaml
   if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
   ```
   Deployments are blocked if the triggering CI run failed.
3. **Artifact Retrieval**: Artifacts are fetched in reusable deployment workflows using `actions/download-artifact@v4` with explicit `run-id` binding (`run-id: ${{ inputs.run_id || github.event.workflow_run.id }}`) and `github-token: ${{ secrets.GITHUB_TOKEN }}`.

### 2.2 AWS IAM OIDC Authentication Protocol

The pipeline utilizes temporary AWS security credentials generated through IAM OpenID Connect (OIDC) federation. Long-lived `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` pair usage is prohibited.

#### Required Action Permissions:
To request the OIDC JSON Web Token (JWT) from GitHub's OIDC provider, reusable CD workflow definitions declare top-level `permissions`:

```yaml
permissions:
  id-token: write
  contents: read
```

#### Authentication Step Contract:
```yaml
- name: Configure AWS Credentials via OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ secrets.AWS_REGION || 'us-east-1' }}
    role-session-name: Alex-CD-GitHubActions
```

---

## 3. Composable CD Reusable Workflows Architecture

The CD pipeline delegates tasks across **3 reusable workflows**:

```mermaid
graph TD
    A["Trigger: CI workflow_run (success on main) / workflow_dispatch"] --> B["cd.yml Orchestrator"]
    B --> C["reusable-terraform-apply.yml"]
    C -->|"Matrix: 2_sagemaker .. 8_enterprise"| D{"Terraform Stacks Applied Successfully?"}
    D -->|"Yes"| E["reusable-deploy-lambdas.yml"]
    D -->|"Yes"| F["reusable-deploy-frontend.yml"]
    E -->|"Download 6 individual Lambda package artifacts into backend/"| G["Deploy via deploy_all_lambdas.py (Without --package)"]
    F -->|"Download frontend-static-build artifact into frontend/out"| H["AWS S3 Sync + CloudFront CDN Invalidation"]
```

#### CD Job Interface Matrix:

| Parent Job ID | Reusable Workflow Target | Responsibility & Scope | Primary Command / CLI | Dependencies (`needs`) |
| :--- | :--- | :--- | :--- | :--- |
| `terraform-apply` | `reusable-terraform-apply.yml` | Matrix provisioning across Terraform stacks (`2_sagemaker` through `8_enterprise`) | `terraform fmt -check`<br>`terraform init`<br>`terraform validate`<br>`terraform apply -auto-approve` | *None (Initial Quality Gate)* |
| `deploy-lambdas` | `reusable-deploy-lambdas.yml` | Lambda resource recreation & deployment using 6 individual CI pre-packaged `.zip` artifacts | `actions/download-artifact@v4`<br>`uv run deploy_all_lambdas.py` | `terraform-apply` |
| `deploy-frontend` | `reusable-deploy-frontend.yml` | Static asset synchronization to S3 & CloudFront cache invalidation using CI pre-built artifacts | `actions/download-artifact@v4`<br>`aws s3 sync frontend/out/ s3://${{ secrets.AWS_S3_FRONTEND_BUCKET }} --delete`<br>`aws cloudfront create-invalidation` | `terraform-apply` |

---

## 3. Implementation Plan & Declarative Workflows

### 3.1 Parent Orchestrator Workflow: `.github/workflows/cd.yml`

```yaml
name: Continuous Deployment

on:
  workflow_run:
    workflows: ["Continuous Integration"]
    types:
      - completed
    branches:
      - main
  workflow_dispatch:
    inputs:
      run_id:
        description: 'CI Workflow Run ID (optional, defaults to triggering/latest CI run)'
        required: false
        type: string
        default: ''

concurrency:
  group: cd-main-${{ github.ref }}
  cancel-in-progress: false

permissions:
  id-token: write
  contents: read

jobs:
  terraform-apply:
    name: Terraform Provisioning
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    uses: ./.github/workflows/reusable-terraform-apply.yml
    secrets: inherit

  deploy-lambdas:
    name: Lambda Agent Deployment
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    needs: terraform-apply
    uses: ./.github/workflows/reusable-deploy-lambdas.yml
    with:
      run_id: ${{ inputs.run_id || (github.event_name == 'workflow_run' && github.event.workflow_run.id) || '' }}
    secrets: inherit

  deploy-frontend:
    name: Frontend Application Deployment
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    needs: terraform-apply
    uses: ./.github/workflows/reusable-deploy-frontend.yml
    with:
      run_id: ${{ inputs.run_id || (github.event_name == 'workflow_run' && github.event.workflow_run.id) || '' }}
    secrets: inherit
```

### 3.2 Reusable Workflow: `.github/workflows/reusable-terraform-apply.yml`

```yaml
name: Reusable Terraform Apply Workflow

on:
  workflow_call:
    secrets:
      AWS_ROLE_ARN:
        required: false
      AWS_REGION:
        required: false
      CLERK_JWKS_URL:
        required: false
      POLYGON_API_KEY:
        required: false
      OPENAI_API_KEY:
        required: false
      ALEX_API_KEY:
        required: false

permissions:
  id-token: write
  contents: read

jobs:
  terraform-plan-and-apply:
    name: Terraform Apply (${{ matrix.stack }})
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: true
      max-parallel: 1
      matrix:
        stack:
          - 2_sagemaker
          - 3_ingestion
          - 4_researcher
          - 5_database
          - 6_agents
          - 7_frontend
          - 8_enterprise

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION || 'us-east-1' }}
          role-session-name: Alex-CD-Terraform-${{ matrix.stack }}

      - name: Setup Terraform CLI
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.0"

      - name: Terraform Format Check
        working-directory: terraform/${{ matrix.stack }}
        run: terraform fmt -check

      - name: Terraform Init
        working-directory: terraform/${{ matrix.stack }}
        run: terraform init

      - name: Terraform Validate
        working-directory: terraform/${{ matrix.stack }}
        run: terraform validate

      - name: Terraform Apply
        working-directory: terraform/${{ matrix.stack }}
        env:
          TF_VAR_aws_region: ${{ secrets.AWS_REGION || 'us-east-1' }}
        run: terraform apply -auto-approve
```

### 3.3 Reusable Workflow: `.github/workflows/reusable-deploy-lambdas.yml`

```yaml
name: Reusable Deploy Lambdas Workflow

on:
  workflow_call:
    inputs:
      run_id:
        description: 'CI Workflow Run ID (optional, defaults to triggering/latest CI run)'
        required: false
        type: string
        default: ''
    secrets:
      AWS_ROLE_ARN:
        required: false
      AWS_REGION:
        required: false
      CLERK_JWKS_URL:
        required: false
      POLYGON_API_KEY:
        required: false
      OPENAI_API_KEY:
        required: false
      ALEX_API_KEY:
        required: false

permissions:
  id-token: write
  contents: read

jobs:
  deploy-lambda-agents:
    name: Deploy Lambda Agents & Subsystems
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION || 'us-east-1' }}
          role-session-name: Alex-CD-Lambda-Deploy

      - name: Download Planner Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-planner
          path: backend/planner
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Download Tagger Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-tagger
          path: backend/tagger
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Download Reporter Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-reporter
          path: backend/reporter
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Download Charter Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-charter
          path: backend/charter
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Download Retirement Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-retirement
          path: backend/retirement
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Download Scheduler Lambda Package Artifact
        uses: actions/download-artifact@v4
        with:
          name: lambda-package-scheduler
          path: backend/scheduler
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python & uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          enable-cache: true
          cache-dependency-glob: "backend/uv.lock"

      - name: Setup Terraform CLI
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.0"

      - name: Install Backend Dependencies
        working-directory: backend
        run: uv sync

      - name: Execute Lambda Deployment Script
        working-directory: backend
        env:
          TF_VAR_aws_region: ${{ secrets.AWS_REGION || 'us-east-1' }}
        run: uv run deploy_all_lambdas.py
```

### 3.4 Reusable Workflow: `.github/workflows/reusable-deploy-frontend.yml`

```yaml
name: Reusable Deploy Frontend Workflow

on:
  workflow_call:
    inputs:
      run_id:
        description: 'CI Workflow Run ID (optional, defaults to triggering/latest CI run)'
        required: false
        type: string
        default: ''
    secrets:
      AWS_ROLE_ARN:
        required: false
      AWS_REGION:
        required: false
      AWS_S3_FRONTEND_BUCKET:
        required: false
      CLOUDFRONT_DISTRIBUTION_ID:
        required: false

permissions:
  id-token: write
  contents: read

jobs:
  deploy-frontend:
    name: Deploy Next.js Frontend & Invalidate CloudFront
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION || 'us-east-1' }}
          role-session-name: Alex-CD-Frontend-Deploy

      - name: Download Frontend Static Export Artifact
        uses: actions/download-artifact@v4
        with:
          name: frontend-static-build
          path: frontend/out
          run-id: ${{ inputs.run_id || github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Sync Static Frontend Artifacts to S3
        run: |
          aws s3 sync frontend/out/ s3://${{ secrets.AWS_S3_FRONTEND_BUCKET }} --delete

      - name: Invalidate CloudFront CDN Cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

---

## 4. Verification & Testing Requirements

### 4.1 Pre-deployment Local Verification Commands

Before committing workflow updates, engineers and AI agents can execute equivalent local verification commands:

```bash
# 1. Verify Terraform Formatting & Validation across Stacks
for dir in terraform/*/; do
  if [ -f "$dir/main.tf" ]; then
    echo "Checking $dir..."
    (cd "$dir" && terraform fmt -check && terraform init -backend=false && terraform validate)
  fi
done

# 2. Verify Lambda Deployment Script with Existing Zip Artifacts
cd backend && uv run deploy_all_lambdas.py

# 3. Verify Frontend Static Directory Sync Format
test -d frontend/out && echo "Frontend build directory exists"
```

### 4.2 GitHub Actions Live Verification Checklist

When triggering a CD pipeline run via `workflow_run` (following CI on `main`) or `workflow_dispatch`:
1. **OIDC Authentication Check**: Confirm `Configure AWS Credentials via OIDC` step successfully assumes `AWS_ROLE_ARN` without requesting long-lived AWS keys.
2. **Terraform Matrix Audit**: Confirm all 7 Terraform stacks (`2_sagemaker` through `8_enterprise`) complete `terraform apply` cleanly in sequential order inside `reusable-terraform-apply.yml`.
3. **Lambda Artifact Download & Deployment Audit**: Confirm `deploy-lambda-agents` in `reusable-deploy-lambdas.yml` downloads all 6 individual Lambda package artifacts (`lambda-package-planner`, `lambda-package-tagger`, `lambda-package-reporter`, `lambda-package-charter`, `lambda-package-retirement`, `lambda-package-scheduler`) into their respective `backend/` subdirectories, recognizes existing `.zip` files, skips re-packaging, taints Lambda functions, and completes deployment cleanly.
4. **Frontend Artifact Download & CDN Audit**: Confirm `deploy-frontend` in `reusable-deploy-frontend.yml` downloads `frontend-static-build` into `frontend/out/`, uploads static assets to `AWS_S3_FRONTEND_BUCKET`, and issues a successful CloudFront cache invalidation request (`Status: InProgress` or `Completed`).
