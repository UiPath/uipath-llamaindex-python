# Context Grounding Retriever Agent

A news aggregator agent that uses LLMs and Context Grounding to fetch, index, and query the latest news articles. This agent demonstrates integration with UiPath Context Grounding, web search (Tavily), and LlamaIndex query engines.

## Description

The Context Grounding Retriever Agent is a multi-step workflow that:

- **Extracts topics**: Uses LLM to identify the main topic from user queries
- **Checks data freshness**: Verifies if indexed data is recent (within 24 hours)
- **Searches the web**: Fetches latest news using Tavily API when data is stale
- **Indexes content**: Adds new articles to UiPath Context Grounding index
- **Queries intelligently**: Uses ReActAgent with context grounding to answer questions

This agent combines LLM reasoning with RAG (Retrieval Augmented Generation) to provide up-to-date, grounded responses.

## Project Initialization

### Prerequisites
- Python 3.10 or higher
- UiPath CLI installed
- UV package manager (optional but recommended)
- Tavily API key (for web search)
- UiPath Context Grounding index named "News-Index"

### Initialize the Project

1. Navigate to the project directory:
```bash
cd context-grounding-retriever-agent
```

2. Install dependencies using UV (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export TAVILY_API_KEY="your_tavily_api_key"
```

## Running Locally

```bash
# setup environment first, then run:
uipath init
uipath run agent --input-file input.json
```

## UiPath Setup

### 1. Authenticate with UiPath

```bash
uipath auth
```

Follow the prompts to authenticate with your UiPath account.

### 2. Create Context Grounding Index

Create an index named "News-Index" in your UiPath Orchestrator under the "Shared" folder.

You can use the steps described in [this sample](https://github.com/UiPath/uipath-langchain-python/tree/main/samples/RAG-quiz-generator) as guidance.

### 3. Pack and Publish the Agent

```bash
uipath pack
uipath publish
```

This creates a package file that is then published to UiPath Orchestrator.

## Input Schema

The agent accepts a query as input:

```json
{
  "query": "What's the latest news about Tesla?"
}
```

### Output Schema

The agent returns a natural language response based on indexed news articles:

```json
{
  "result": "string (LLM-generated answer with citations)"
}
```

## Configuration

Key configuration values in `main.py`:

- `INDEX_NAME = "News-Index"` - Context Grounding index name
- `FOLDER_PATH = "Shared"` - Orchestrator folder path
- `FRESHNESS_HOURS = 24` - Data freshness threshold in hours

## Workflow Steps

1. **Extract Topic**: LLM extracts the main topic from the user query
2. **Check Freshness**: Verifies if indexed data is less than 24 hours old
3. **Search Web** (if stale): Fetches latest news using Tavily API
4. **Add to Index** (if stale): Ingests new articles into Context Grounding
5. **Wait for Ingestion**: Polls until indexing completes
6. **Query Index**: Uses ReActAgent to answer the query using indexed data

