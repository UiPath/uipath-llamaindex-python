import json
import os
import sys

print("Checking triage agent output...")

# Check NuGet package
uipath_dir = ".uipath"
if not os.path.exists(uipath_dir):
    print("NuGet package directory (.uipath) not found")
    sys.exit(1)

nupkg_files = [f for f in os.listdir(uipath_dir) if f.endswith(".nupkg")]
if not nupkg_files:
    print("NuGet package file (.nupkg) not found in .uipath directory")
    sys.exit(1)

print(f"NuGet package found: {nupkg_files[0]}")

# Check agent output file
output_file = "__uipath/output.json"
if not os.path.isfile(output_file):
    print("Agent output file not found")
    sys.exit(1)

print("Agent output file found")

# Check status and output
try:
    with open(output_file, "r", encoding="utf-8") as f:
        output_data = json.load(f)

    # Check status
    status = output_data.get("status")
    if status != "successful":
        print(f"Agent execution failed with status: {status}")
        sys.exit(1)

    print("Agent execution status: successful")

    # Check output field exists
    if "output" not in output_data:
        print("Missing 'output' field in agent response")
        sys.exit(1)

    output_content = output_data["output"]

    # For OpenAI Agents, output is typically the message content
    # It could be a string or structured data depending on output_type
    if isinstance(output_content, str):
        response = output_content
        if not response or response.strip() == "":
            print("Response is empty")
            sys.exit(1)
        print(
            f"Response: {response[:100]}..."
            if len(response) > 100
            else f"Response: {response}"
        )
    elif isinstance(output_content, dict):
        # If structured output, just verify it's not empty
        if not output_content:
            print("Output is empty")
            sys.exit(1)
        print(f"Structured output: {json.dumps(output_content, indent=2)[:200]}...")
    else:
        print(f"Output type: {type(output_content)}")
        print(f"Output value: {output_content}")

    print("Required fields validation passed")
    print("Triage agent working correctly.")

except Exception as e:
    print(f"Error checking output: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
