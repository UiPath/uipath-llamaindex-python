FROM ghcr.io/astral-sh/uv:python3.12-bookworm

WORKDIR /app

COPY . .

WORKDIR /app/testcases/simple-hitl-agent

RUN uv sync

ARG CLIENT_ID
ARG CLIENT_SECRET
ARG BASE_URL

RUN if [ -z "$CLIENT_ID" ]; then echo "CLIENT_ID build arg is required" && exit 1; fi
RUN if [ -z "$CLIENT_SECRET" ]; then echo "CLIENT_SECRET build arg is required" && exit 1; fi
RUN if [ -z "$BASE_URL" ]; then echo "BASE_URL build arg is required" && exit 1; fi

# Set environment variables for runtime
ENV CLIENT_ID=$CLIENT_ID
ENV CLIENT_SECRET=$CLIENT_SECRET
ENV BASE_URL=$BASE_URL
ENV TAVILY_API_KEY=${TAVILY_API_KEY:-""}
ENV UIPATH_TENANT_ID=${UIPATH_TENANT_ID:-""}
ENV UIPATH_JOB_KEY=8c6a342e-036e-492c-a3d2-99e66f6554ce

# Authenticate with UiPath during build
RUN uv run uipath auth --client-id="$CLIENT_ID" --client-secret="$CLIENT_SECRET" --base-url="$BASE_URL"

RUN uv run uipath pack

# Run the agent with input from input.json
RUN AGENT_INPUT=$(cat input.json) && uv run uipath run agent "$AGENT_INPUT"
RUN HUMAN_RESPONSE=$(cat human_response.json) && uv run uipath run agent "$HUMAN_RESPONSE" --resume

# Run the Python assert script to validate output
RUN python src/assert.py