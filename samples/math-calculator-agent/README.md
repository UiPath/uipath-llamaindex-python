# Math Calculator Agent

A deterministic workflow agent that performs mathematical calculations on a list of numbers. This agent calculates the sum, count, and average of the provided numbers.

## Description

The Math Calculator Agent is a simple workflow that:

- **Calculates sum**: Adds all numbers in the input list
- **Counts items**: Returns the total count of numbers provided
- **Calculates average**: Computes the mean value of all numbers
- **Deterministic output**: Returns structured JSON responses for easy testing and integration

## Project Initialization

### Prerequisites
- Python 3.10 or higher
- UiPath CLI installed
- UV package manager (optional but recommended)

### Initialize the Project

1. Navigate to the project directory:
```bash
cd math-calculator-agent
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
uipath run agent --input-file ./testcases/input/test_1.json
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
  "numbers": [integer array]
}
```
### Output Schema

The agent returns a structured JSON response:

```json
{
  "sum_result": integer,
  "count": integer,
  "average": number
}
```

## Test Cases

The `testcases/` directory contains 5 deterministic test cases to validate the agent's behavior.

**Test 1**: Calculate sum, count, and average of [10, 20, 30, 40, 50]

**Test 2**: Single number calculation [100]

**Test 3**: Three numbers [5, 15, 25]

**Test 4**: Mix of positive and negative numbers [-10, 10, -5, 5]

**Test 5**: Six numbers (multiples of 7) [7, 14, 21, 28, 35, 42]

## Running Test Cases

To run the test cases in UiPath Orchestrator:

1. Start a job with the input from `testcases/input/test_X.json`
2. Compare the output with `testcases/expected_output/test_X_expected_output.json`
