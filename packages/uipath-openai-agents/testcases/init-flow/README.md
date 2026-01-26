# OpenAI Agents Integration Test - Init Flow

This testcase validates the complete init-flow for OpenAI Agents SDK integration with UiPath.

## What it tests

1. **Project Setup**: Creates a new UiPath agent project using `uipath new agent`
2. **Initialization**: Runs `uipath init` to generate configuration files
3. **Packaging**: Packs the agent into a NuGet package
4. **Deployment Execution**: Runs the agent with UiPath platform integration
5. **Local Execution**: Runs the agent locally with tracing enabled
6. **Output Validation**: Validates the agent output structure and status
7. **Trace Validation**: Verifies that expected OpenTelemetry spans are generated

## Files

- **pyproject.toml**: Project dependencies and configuration
- **input.json**: Test input for the agent
- **run.sh**: Main test script that executes all steps
- **expected_traces.json**: Expected OpenTelemetry spans for validation
- **src/assert.py**: Assertion script that validates outputs and traces

## Expected Traces

The test validates that the following spans are generated:

- **Agent workflow**: OpenAI Agents SDK top-level agent span (AGENT kind)
- **response**: OpenAI Responses API call span (LLM kind) - note that OpenAI Agents SDK uses the Responses API, not ChatCompletion

## Running the test

```bash
cd testcases/init-flow
bash run.sh
```

The test requires:
- `CLIENT_ID`: UiPath OAuth client ID
- `CLIENT_SECRET`: UiPath OAuth client secret
- `BASE_URL`: UiPath platform base URL

## Success Criteria

The test passes if:

1. NuGet package (.nupkg) is created successfully
2. Agent executes without errors (status: "successful")
3. Output contains the expected "result" field
4. Local run output contains "Successful execution."
5. All expected OpenTelemetry spans are present in traces.jsonl
