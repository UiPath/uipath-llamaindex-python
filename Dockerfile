FROM ghcr.io/astral-sh/uv:python3.12-bookworm

WORKDIR /app

COPY . .

RUN uv sync

ARG CLIENT_ID
ARG CLIENT_SECRET
ARG BASE_URL
ARG AGENT_INPUT
ARG SKIP_HUMAN_APPROVAL=false
ARG USE_REGULAR_INTERRUPT=false

# Validate required environment variables
RUN if [ -z "$CLIENT_ID" ]; then echo "CLIENT_ID build arg is required" && exit 1; fi
RUN if [ -z "$CLIENT_SECRET" ]; then echo "CLIENT_SECRET build arg is required" && exit 1; fi
RUN if [ -z "$BASE_URL" ]; then echo "BASE_URL build arg is required" && exit 1; fi
RUN if [ -z "$AGENT_INPUT" ]; then echo "AGENT_INPUT build arg is required" && exit 1; fi

# Set environment variables for runtime
ENV CLIENT_ID=$CLIENT_ID
ENV CLIENT_SECRET=$CLIENT_SECRET
ENV BASE_URL=$BASE_URL
ENV TAVILY_API_KEY=${TAVILY_API_KEY:-""}
ENV UIPATH_TENANT_ID=${UIPATH_TENANT_ID:-""}

# for the ticket_classification
ENV SKIP_HUMAN_APPROVAL=$SKIP_HUMAN_APPROVAL
ENV USE_REGULAR_INTERRUPT=$USE_REGULAR_INTERRUPT

# Authenticate with UiPath during build
RUN uv run uipath auth --client-id="$CLIENT_ID" --client-secret="$CLIENT_SECRET" --base-url="$BASE_URL"


RUN uv run uipath run agent "$AGENT_INPUT"

RUN if [ "$USE_REGULAR_INTERRUPT" = "true" ] && echo "$AGENT_INPUT" | grep -q '"ticket_id"'; then \
      echo "Running resume for ticket classification with regular interrupt..."; \
      uv run uipath run agent '{"Answer": true}' --resume; \
    else \
      echo "Skipping resume - either not ticket classification or USE_REGULAR_INTERRUPT=false"; \
    fi
