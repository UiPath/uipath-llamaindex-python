# PTO Approval Agent

A deterministic Human-in-the-Loop (HITL) workflow agent for processing Paid Time Off (PTO) requests. The agent uses API triggers to resume execution after receiving human input via HITL.

## Description

The PTO Approval Agent processes employee time-off requests with the following logic:

- **Auto-approval**: PTO requests for 2 days or less are automatically approved
- **Manager approval required**: PTO requests for 3+ days require human (manager) approval via HITL
- **Validation**: Validates date formats and ensures end date is after start date
- **Deterministic output**: Returns structured JSON responses for easy testing and integration

## Project Initialization

### Prerequisites
- Python 3.10 or higher
- UiPath CLI installed
- UV package manager (optional but recommended)

### Initialize the Project

1. Navigate to the project directory:
```bash
cd pto-approval-agent
```

2. Install dependencies using UV (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirements.txt
```
## Running Locally

```bash
# setup environment first, then run:
uipath init
uipath run agent --input-file ./testcases/input/<name_of_your_test_case>.json
```

## UiPath Setup

### 1. Authenticate with UiPath

```bash
uipath auth
```

Follow the prompts to authenticate with your UiPath account.

### 2. Pack and Publish the Agent

```bash
uipath pack
uipath publish
```

This creates a package file that is then published to UiPath Orchestrator.

## Input Schema

The agent accepts the following structured input:

```json
{
  "employee_name": "string",
  "start_date": "string (YYYY-MM-DD format)",
  "end_date": "string (YYYY-MM-DD format)",
  "reason": "string"
}
```

### Output Schema

The agent returns a structured JSON response:

```json
{
  "status": "auto-approved | approved | denied | error",
  "employee": "string",
  "start_date": "string",
  "end_date": "string",
  "days": "number",
  "reason": "string",
  "message": "string"
}
```

## Test Cases

The `testcases/` directory contains 5 deterministic test cases to validate the agent's behavior.

**Test 1**: Auto-approval for 2-day PTO request

**Test 2**: Manager approves 6-day PTO request (HITL: yes)

**Test 3**: Manager denies 11-day PTO request (HITL: no)

**Test 4**: Validation error for invalid date range

**Test 5**: Manager approves 5-day PTO request (HITL: yes)

## Running Test Cases

To run the test cases in UiPath Orchestrator:

1. Start a job with the input from `test_X.json`
2. If HITL is required, provide the response from `test_X_resume.json` when prompted
3. Compare the output with `test_X_expected_output.json`

