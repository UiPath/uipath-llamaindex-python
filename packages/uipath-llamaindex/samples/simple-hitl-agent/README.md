# Simple HITL Agent

A LlamaIndex agent that demonstrates Human-in-the-Loop (HITL) functionality by requesting approval before researching companies.

## Overview

This agent uses a tool function that pauses execution and waits for human approval before proceeding with research.

## How it works

1. Agent receives a research request
2. Calls `may_research_company` tool which suspends execution
3. Waits for human approval (yes/no)
4. Resumes and provides research results if approved

## Running the agent

**Initial run (suspends for approval):**
```bash
uipath run agent '{"user_msg": "please research uipath"}'
```

**Resume with human response:**
```bash
uipath run agent '{"response": "yes"}' --resume
```

## Key features

- **HITL Pattern**: Demonstrates workflow suspension and resumption
- **Human approval**: Requires explicit permission before executing research
- **State persistence**: Context is saved when suspended and restored on resume
