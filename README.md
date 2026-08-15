# Alex - the Agentic Learning Equities Explainer

## Multi-agent Enterprise-Grade SaaS Financial Planner

![Course Image](assets/alex.png)

_If you're looking at this in Cursor, please right click on the filename in the Explorer on the left, and select "Open preview", to view it in formatted glory._

### Welcome to The Capstone Project for Week 3 and Week 4!

#### The directories:

1. **guides** - step-by-step deployment guides to deploy to production
2. **docs** - system documentation and the `docs/specs/` LLM Agent Harness for specification-driven development
3. **backend** - the agent code, organized into subdirectories, each a uv project (as is the backend parent directory)
4. **frontend** - a NextJS React frontend integrated with Clerk
5. **terraform** - separate terraform subdirectories with state for each part
6. **scripts** - deployment and utility scripts

### LLM Agent Harness (`docs/`)

Project Alex utilizes the `docs/` directory—specifically `docs/specs/`—as an **LLM Agent Document Harness**.

- **System Context Guide**: [docs/About.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy.nosync/projects/alex/docs/About.md) provides high-density architectural context, component linkages, multi-agent topologies, and environment variable requirements for AI assistants.
- **Specification Harness**: [docs/specs/](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy.nosync/projects/alex/docs/specs/) establishes machine-readable, single-source-of-truth technical contracts for database schemas, agent SDK contracts, API DTOs, and infrastructure automation. AI agents inspect and follow these specs before executing codebase changes.

### Continuous Integration (`.github/workflows/ci.yml`)

Project Alex includes a GitHub Actions Continuous Integration (CI) pipeline designed for rapid PR feedback and quality gate validation:

- **CI Specification**: Defined in [docs/specs/infrastructure/github_ci_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy.nosync/projects/alex/docs/specs/infrastructure/github_ci_spec.md).
- **Workflow Pipeline**: [.github/workflows/ci.yml](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy.nosync/projects/alex/.github/workflows/ci.yml) executes quality checks and builds production release artifacts (`frontend-static-build` and `lambda-agent-packages`) uploaded via `actions/upload-artifact@v4`.
- **Performance SLA**: Optimized with `uv`, `npm`, and Next.js build layer caching to complete in **< 120 seconds** (~65-75s average).

#### Local Verification Commands

```bash
# 1. Backend Linting & Pytest Suite
cd backend && uv run --with ruff ruff check . && uv run pytest tests/ -v

# 2. Frontend Linting & Production Build
cd frontend && npm run lint && npm run build
```

### Production Secrets Management (AWS Secrets Manager)

Project Alex manages production API key secrets centrally via **AWS Secrets Manager** (`alex/production/secrets`), eliminating static production secrets in GitHub repository settings or `.tfvars` files:

- **Secrets Specification**: Defined in [docs/specs/infrastructure/secrets_management_spec.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy.nosync/projects/alex/docs/specs/infrastructure/secrets_management_spec.md).
- **One-Time Setup Script**: Run the setup script to populate or update `alex/production/secrets` in your AWS account:
   ```bash
   uv run scripts/populate_aws_secrets.py
   ```
- **Infrastructure & Application Integration**: Terraform stacks (`4_researcher`, `6_agents`, `7_frontend`) fetch secrets directly from AWS Secrets Manager at `apply` time via `data "aws_secretsmanager_secret_version"`, populating Lambda / App Runner environment variables seamlessly with zero Python code changes required.

#### Order of play:

##### Week 3

- On Week 3 Day 3, we will do 1_permissions and 2_sagemaker
- On Week 3 Day 4, we will do 3_ingest
- On Week 3 Day 5, we will do 4_researcher

##### Week 4

- On Week 4 Day 1, we will do 5_database
- On Week 4 Day 2, we will do 6_agents
- On Week 4 Day 3, we will do 7_frontend
- On Week 4 Day 4, we will do 8_enterprise

#### Keep in mind

- Please submit your community_contributions, including links to your repos, in the production repo community_contributions folder
- Regularly do a git pull to get the latest code
- Reach out in Udemy or email (ed@edwarddonner.com) if I can help! This is a gigantic project and I am here to help you deliver it!