# Company Research Agent

This UiPath LlamaIndex agent assists in researching companies using AI and human-in-the-loop (HITL) collaboration. It triggers external processes, waits for human input, and generates validated reports.

## Features
* Triggers a UiPath workflow to research and analyze the given company name
* Incorporates human feedback to validate the analysis
* Produces the final, validated company report

## Getting Started

### 1. Clone the Repository

```sh
git clone https://github.com/your-org/uipath-llamaindex-python.git
cd uipath-llamaindex-python/samples/multi-agent
```

### 2. Set Up Python Environment

```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Or use `pyproject.toml` with pip:
```sh
pip install .
```

### 3. Configure Environment

Copy `.env.template` to `.env` and fill in your secrets (API keys, tokens, etc.)

### 4. Run the Agent

```sh
uipath run agent --file ./input.json
```

> **Warning:** An agent can invoke itself if needed, but this must be done with caution. Be mindful that using the same name for invocation may lead to unintentional loops. To prevent recursion issues, implement safeguards like exit conditions.

### 5. Resume

To approve the rules and commit them use:
```sh
uipath run agent true --resume
```

Example:
```sh
uipath run agent --file ./input.json
```

### Deployment Guide

To run the company-researcher-agent on the UiPath Cloud Platform, follow this guide:
[Ticket Classification Sample Deployment](https://github.com/UiPath/uipath-langchain-python/tree/main/samples/ticket-classification)
