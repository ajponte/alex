# Specification: Automated Research Scheduler & Unified Lambda Deployment 📋

## Status: APPROVED
**Module**: `infrastructure / scheduler / deployment`  
**Target Files**: 
- [terraform/4_researcher/main.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/4_researcher/main.tf)
- [terraform/4_researcher/variables.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/4_researcher/variables.tf)
- [terraform/4_researcher/outputs.tf](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/terraform/4_researcher/outputs.tf)
- [backend/scheduler/lambda_function.py](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/scheduler/lambda_function.py)
- [backend/deploy_all_lambdas.py](file:///Users/aponte/personal_workspace/agent_engineering_production_udemy/projects/alex/backend/deploy_all_lambdas.py)

---

## 1. Executive Summary & Objectives

This specification defines the technical contract for:
1. **Daily Automated Research Schedule**: Transitioning the market research trigger from high-frequency polling (`rate(2 hours)`) to a daily schedule (`5:00 PM PST`), yielding a **~91% reduction in Bedrock LLM token consumption** (~$33.00/month cost savings).
2. **Event Payload Context Synchronization**: Eliminating dual-source-of-truth configuration drift by passing schedule expressions directly inside the EventBridge target event payload.
3. **Unified Lambda Deployment Orchestration**: Updating `backend/deploy_all_lambdas.py` to package and deploy all 7 platform Lambda functions (Part 6 Agent Orchestra + Part 4 Researcher & Scheduler) by default.

---

## 2. Automated Research Scheduler Specification

### 2.1 Schedule Expression & Timezone

```hcl
variable "schedule_expression" {
  description = "Schedule expression for the automated research scheduler"
  type        = string
  default     = "cron(0 17 * * ? *)"
}

variable "schedule_expression_timezone" {
  description = "Timezone for the schedule expression"
  type        = string
  default     = "America/Los_Angeles"
}
```

- **Cron Pattern**: `cron(0 17 * * ? *)` (Triggers every day at 17:00 / 5:00 PM).
- **Timezone Boundary**: `America/Los_Angeles` (PST/PDT aware).
- **Cost Impact**:
  - `rate(2 hours)`: 12 executions/day = 360 runs/month ($\approx$ $36.00/month Bedrock tokens).
  - `cron(0 17 * * ? *)`: 1 execution/day = 30 runs/month ($\approx$ $3.00/month Bedrock tokens).
  - **Net Savings**: **~$33.00 / month saved**.

### 2.2 Event Payload Synchronization Protocol

To prevent configuration drift between EventBridge and Lambda environment variables, EventBridge passes schedule parameters directly in the invocation payload:

```hcl
resource "aws_scheduler_schedule" "research_schedule" {
  count = local.scheduler_active ? 1 : 0
  name  = "alex-research-schedule"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_expression_timezone

  target {
    arn      = aws_lambda_function.scheduler_lambda[0].arn
    role_arn = aws_iam_role.eventbridge_role[0].arn

    input = jsonencode({
      schedule_expression          = var.schedule_expression
      schedule_expression_timezone = var.schedule_expression_timezone
    })
  }
}
```

### 2.3 Scheduler Lambda Handler Contract (`backend/scheduler/lambda_function.py`)

The Lambda function extracts schedule details from the incoming event payload and forwards context to the researcher container:

```python
def handler(event, context):
    """Trigger the research endpoint on App Runner / Container Lambda."""
    _LOGGER.info(f"Received scheduler trigger event: {event}")
    
    app_runner_url = os.environ.get('APP_RUNNER_URL')
    if not app_runner_url:
        raise ValueError("`APP_RUNNER_URL` environment variable not set")

    app_runner_url = _normalize_url(app_runner_url)
    url = f"https://{app_runner_url}/research"

    # Extract schedule context from EventBridge target payload
    schedule_context = {}
    if isinstance(event, dict):
        if "schedule_expression" in event:
            schedule_context["schedule_expression"] = event["schedule_expression"]
        if "schedule_expression_timezone" in event:
            schedule_context["schedule_expression_timezone"] = event["schedule_expression_timezone"]

    data = json.dumps(schedule_context).encode('utf-8')
    return _trigger_lambda_request(
        req=_make_request(url, data),
        req_timeout=DEFAULT_LAMBDA_REQUEST_TIMEOUT
    )
```

---

## 3. Unified Lambda Deployment Specification (`deploy_all_lambdas.py`)

### 3.1 Default Scope

Running `uv run deploy_all_lambdas.py` automatically handles packaging, tainting, and deploying **all 7 platform Lambda functions**:

1. **Part 6 Agent Orchestra** (via `terraform/6_agents/`):
   - `planner` (`aws_lambda_function.planner`)
   - `tagger` (`aws_lambda_function.tagger`)
   - `reporter` (`aws_lambda_function.reporter`)
   - `charter` (`aws_lambda_function.charter`)
   - `retirement` (`aws_lambda_function.retirement`)
2. **Part 4 Research Subsystem** (via `terraform/4_researcher/`):
   - `scheduler` (`aws_lambda_function.scheduler_lambda`)
   - `researcher` (`aws_lambda_function.researcher[0]`)

### 3.2 Packaging Dispatch Rules

- **Standard Agents**: Packaged via `package_docker.py` within each agent directory.
- **Scheduler Lambda**: Packaged via `backend/package_scheduler.py` into `backend/scheduler/lambda_function.zip`.

### 3.3 Command Line Interface (CLI)

```bash
# Standard Deployment: Packages missing zips and deploys all 7 Lambdas
cd backend
uv run deploy_all_lambdas.py

# Force Re-packaging: Forces re-packaging of all 7 Lambda zip files prior to Terraform apply
uv run deploy_all_lambdas.py --package
```

---

## 4. Verification & Testing Requirements

1. **Unit Tests**:
   - `backend/tests/scheduler/test_lambda_function.py` must pass with 100% success.
2. **Live Schedule Verification**:
   - `aws scheduler get-schedule --name alex-research-schedule --region us-west-2` must confirm:
     - `"ScheduleExpression": "cron(0 17 * * ? *)"`
     - `"ScheduleExpressionTimezone": "America/Los_Angeles"`
3. **Packaging Verification**:
   - `backend/scheduler/lambda_function.zip` size must be verified (< 1 MB).
