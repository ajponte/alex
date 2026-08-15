# Specification: LLM Agent Harness Architecture & Specification-Driven Protocol

## Status: APPROVED
**Module**: `docs / specs / harness`  
**Target Files**:
- [README.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/README.md)
- [docs/About.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/About.md)
- [docs/specs/](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/specs/)

---

## 1. Executive Summary & Purpose

This specification establishes the formal architecture and operational protocol for the **LLM Agent Harness** in Project Alex (`docs/specs/`). 

The harness provides an explicit, machine-readable, and human-auditable framework governing how AI agents (Antigravity, Cursor, subagents, and LLM coding tools) inspect system context, author technical specifications, execute code modifications, and perform empirical runtime verification.

---

## 2. Harness Architecture & Directory Topology

The `docs/` directory is partitioned into system context documentation (`docs/About.md`) and component specification subdirectories (`docs/specs/`):

```
docs/
├── About.md                                                      # High-density system context & architecture guide
└── specs/                                                        # LLM Agent Document Harness
    ├── llm_agent_harness_spec.md                                # Harness architecture & agent protocol (this file)
    ├── infrastructure/                                           # Terraform, deployment & schedule specifications
    │   └── scheduler_and_deployment_spec.md                      # EventBridge schedule & deploy_all_lambdas.py spec
    ├── database/                                                 # SQL schema & UNLOGGED cache specifications
    ├── agents/                                                   # Agent SDK prompt, tool, & model contracts
    └── api/                                                      # FastAPI endpoint contracts & Pydantic DTO specifications
```

---

## 3. Specification-Driven Agent Workflow Protocol

AI agents working on Project Alex MUST adhere to the following three-phase protocol when undertaking new feature development, refactoring, or infrastructure updates:

### Phase 1: Context Inspection & Specification Alignment
1. **Context Discovery**: Prior to writing or modifying code, agents inspect [docs/About.md](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/docs/About.md) for overall architectural linkages, model routing policies, and environment variable requirements.
2. **Spec Verification**: Agents inspect `docs/specs/` to locate existing specifications relevant to the target module (e.g., `infrastructure/`, `database/`, `agents/`, `api/`).
3. **Spec Authoring**: If no specification exists for a non-trivial architectural change, the agent authors a formal specification markdown document in `docs/specs/<domain>/<spec_name>.md` detailing target files, schema definitions, interface signatures, and verification rules.

### Phase 2: Single Source of Truth Enforcement
1. **Deterministic Scoping**: Code modifications must adhere strictly to the target files, type signatures, and data contracts established in the target specification file.
2. **Zero Architectural Guessing**: Agents are prohibited from inferring unvalidated schema fields, hardcoding non-standard environment variables, or creating redundant helper utilities outside spec contracts.

### Phase 3: Scoped Implementation & Empirical Verification
1. **Targeted Code Changes**: Modifications are executed cleanly against the codebase using scoped code-editing tools.
2. **Verification Command Execution**: Tasks are declared complete ONLY after running empirical verification commands (e.g., `pytest`, `terraform plan`, `aws` CLI checks).

---

## 4. Specification Template Standard

All specification documents residing within `docs/specs/` must follow this standardized Markdown structure:

```markdown
# Specification: <Feature / Component Name>

## Status: <DRAFT | APPROVED | DEPRECATED>
**Module**: `<domain> / <component>`
**Target Files**:
- [path/to/file1.py](file:///absolute/path/to/file1.py)
- [path/to/file2.tf](file:///absolute/path/to/file2.tf)

---

## 1. Executive Summary & Objectives
<High-level summary of the architectural change, business value, and technical scope>

## 2. Technical Contracts & Interface Specifications
<Explicit API signatures, Pydantic schemas, HCL resource definitions, or Python class contracts>

## 3. Implementation Plan & Execution Steps
<Step-by-step file edits and structural modifications>

## 4. Verification & Testing Requirements
<Exact commands (pytest, terraform plan, aws CLI) required to empirically validate success>
```
