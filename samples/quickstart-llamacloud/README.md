# Quickstart LlamaCloud Agent

This project demonstrates how to integrate UiPath with LlamaIndex and LlamaCloud for document search and travel assistance workflows using a `FunctionAgent`.

## Overview

The Quickstart LlamaCloud Agent provides a FunctionAgent that can:
1. Search company travel policies and rates from the `company-policy` index
2. Search user's personal travel preferences from the `personal-preferences` index
3. Generate comprehensive travel recommendations combining both sources
4. Deploy as a UiPath agent for automation workflows

## Features

- **FunctionAgent Architecture**: Uses LlamaIndex's FunctionAgent for intelligent tool selection
- **Dual Index Search**: Searches both company policies and personal preferences
- **Smart Tool Selection**: Automatically chooses the right tools based on user queries
- **Comprehensive Travel Guidance**: Combines policy and preference information
- **UiPath Integration**: Ready for deployment to UiPath Cloud

## Prerequisites

- Python 3.10+
- UiPath Cloud account
- OpenAI API key
- LlamaCloud account with API access

## Setup


### 1. Set Up Virtual Environment

We recommend using `uv` for package management:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install the project dependencies
uv sync
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys and configuration
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `LLAMACLOUD_API_KEY`: Your LlamaCloud API key (find it under API keys in your LlamaCloud account)
- `LLAMACLOUD_ORG_ID`: Your LlamaCloud organization ID (find it under settings in your LlamaCloud account)
- `LLAMACLOUD_PROJECT_NAME`: Your LlamaCloud project name
- `LLAMACLOUD_INDEX_1_NAME`: First index name (e.g., "company-policy")
- `LLAMACLOUD_INDEX_2_NAME`: Second index name (e.g., "personal-preferences")

## 4. Authenticate With UiPath

Install the uipath cli, e.g. using `pipx install uipath`.

Next, auth with uipath:

```shell
> uipath auth
⠋ Authenticating with UiPath ...
🔗 If a browser window did not open, please open the following URL in your browser: [LINK]
👇 Select tenant:
  0: Tenant1
  1: Tenant2
Select tenant number: 0
Selected tenant: Tenant1
✓  Authentication successful.
```

### 5. Configure LlamaCloud Indexes

- Set up your indexes in LlamaCloud with the names specified in your `.env` file
- You can drag and drop the files in `/sample_data` into the relevant indexes
- Update the project name and organization ID in your `.env` file
- Ensure your API key has access to the specified indexes

### 6. Run Locally

```bash
# Simply run the agent with a query
uipath run agent '{"user_msg": "What are the travel rates for New York?"}'
```

```bash
# Run the agent in CLI dev mode (you can enter the input user message and look at traces)
uipath dev
```

### 7. Run as a UiPath Deployment

1. **Package your project:**
   ```bash
   uipath pack
   ```

2. **Publish to UiPath Cloud:**
   ```bash
   uipath publish --my-workspace
   ```

3. **Invoke the agent:**
   ```bash
   uipath invoke agent '{"user_msg": "What are the travel rates for New York?"}'
   ```
   
## Available Functions

The agent has access to three main functions:

### 1. `search_company_policy(query: str)`
Searches the company policy index for travel rates, guidelines, and company policies.
- **Use case**: "What are the travel rates for New York?"
- **Returns**: Company policy information with source files and relevance scores

### 2. `search_personal_preferences(query: str)`
Searches the personal preferences index for user's travel preferences and requirements.
- **Use case**: "What are my travel preferences?"
- **Returns**: Personal preference information with source files and relevance scores

### 3. `get_travel_recommendation(query: str)`
Generates comprehensive travel recommendations combining both company policies and personal preferences.
- **Use case**: "Give me travel recommendations for a business trip"
- **Returns**: Combined analysis from both indexes



## Example Queries

- "What are the travel rates for California?"
- "What are my travel preferences?"
- "Give me travel recommendations for a business trip to New York"
- "What are the company travel guidelines?"
- "What are my personal travel requirements?"

## Dependencies

- `uipath-llamaindex`: UiPath LlamaIndex integration
- `llama-index-llms-openai`: OpenAI LLM integration
- `llama-cloud-services`: LlamaCloud integration 
