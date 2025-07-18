import json
import os
import sys

print("Checking simple HITL agent output...")

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

# Check status and required fields
try:
    with open(output_file, "r", encoding="utf-8") as f:
        output_data = json.load(f)

    # Check status
    status = output_data.get("status")
    if status != "successful":
        print(f"Agent execution failed with status: {status}")
        sys.exit(1)

    print("Agent execution status: successful")

    # Check required fields for simple HITL agent
    if "output" not in output_data:
        print("Missing 'output' field in agent response")
        sys.exit(1)

    output_content = output_data["output"]

    # Check for agent response
    if "response" not in output_content:
        print("Missing 'response' field in output")
        sys.exit(1)

    response = output_content["response"]

    # Check response structure
    if "blocks" not in response:
        print("Missing 'blocks' field in response")
        sys.exit(1)

    blocks = response["blocks"]
    if not blocks or len(blocks) == 0:
        print("No response blocks found")
        sys.exit(1)

    # Check for text content
    text_block = blocks[0]
    if "text" not in text_block:
        print("Missing 'text' field in response block")
        sys.exit(1)

    response_text = text_block["text"]

    # Check for tool calls (function execution)
    if "tool_calls" not in output_content:
        print("Missing 'tool_calls' field - function was not called")
        sys.exit(1)

    tool_calls = output_content["tool_calls"]
    if not tool_calls or len(tool_calls) == 0:
        print("No tool calls found - function was not executed")
        sys.exit(1)

    # Validate the specific function call
    first_call = tool_calls[0]
    expected_fields = ["tool_name", "tool_kwargs", "tool_id"]

    for field in expected_fields:
        if field not in first_call:
            print(f"Missing '{field}' in tool call")
            sys.exit(1)

    # Check if the correct function was called
    if first_call["tool_name"] != "may_research_company":
        print(
            f"Wrong function called: {first_call['tool_name']}, expected 'may_research_company'"
        )
        sys.exit(1)

    # Check function parameters
    tool_kwargs = first_call["tool_kwargs"]
    if "company_name" not in tool_kwargs:
        print("Missing 'company_name' parameter in function call")
        sys.exit(1)

    company_name = tool_kwargs["company_name"]

    # Check if response indicates successful approval
    if "research" not in response_text.lower() or "uipath" not in response_text.lower():
        print("Response doesn't indicate successful research approval")
        sys.exit(1)

    print("All HITL-specific validations passed:")
    print(f"Agent response: {response_text}")
    print(f"Function called: {first_call['tool_name']}")
    print(f"Company researched: {company_name}")
    print(f"Tool call ID: {first_call['tool_id']}")

    print("Simple HITL agent working correctly.")

except Exception as e:
    print(f"Error checking output: {e}")
    sys.exit(1)
