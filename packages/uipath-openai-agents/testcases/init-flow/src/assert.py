import json
import os

from trace_assert import assert_traces

print("Checking init-flow output...")

# Check NuGet package
uipath_dir = ".uipath"
assert os.path.exists(uipath_dir), "NuGet package directory (.uipath) not found"

nupkg_files = [f for f in os.listdir(uipath_dir) if f.endswith(".nupkg")]
assert nupkg_files, "NuGet package file (.nupkg) not found in .uipath directory"

print(f"NuGet package found: {nupkg_files[0]}")

# Check agent output file
output_file = "__uipath/output.json"
assert os.path.isfile(output_file), "Agent output file not found"

print("Agent output file found")

# Check status and required fields
with open(output_file, "r", encoding="utf-8") as f:
    output_data = json.load(f)

# Check status
status = output_data.get("status")
assert status == "successful", f"Agent execution failed with status: {status}"

print("Agent execution status: successful")

# Check required fields for OpenAI agent
assert "output" in output_data, "Missing 'output' field in agent response"

output_content = output_data["output"]
assert "result" in output_content, "Missing 'result' field in output"

result = output_content["result"]
assert result and isinstance(result, (str, dict, list)), (
    "Result field is empty or invalid type"
)

print(f"Result field validated: {type(result).__name__}")

# Check local run output
with open("local_run_output.log", "r", encoding="utf-8") as f:
    local_run_output = f.read()

# Check if response contains 'Successful execution.'
assert "Successful execution." in local_run_output, (
    f"Response does not contain 'Successful execution.'. Actual response: {local_run_output}"
)

print("Local run output validated")

# Check traces
with open(".uipath/traces.jsonl", "r", encoding="utf-8") as f:
    local_run_traces = f.read()
    print(f"Traces generated: {len(local_run_traces)} bytes")

# Simple trace assertions - just check that expected spans exist
assert_traces(".uipath/traces.jsonl", "expected_traces.json")

print("All validations passed successfully!")
