# UiPath Agents Runtime Integrations

A collection of Python SDKs that enable developers to build and deploy agents to the UiPath Cloud Platform using different agent frameworks. These packages provide programmatic interaction with UiPath Cloud Platform services and human-in-the-loop (HITL) semantics through Action Center integration.

All packages are extensions to the [UiPath Python SDK](https://github.com/UiPath/uipath-python) and implement the [UiPath Runtime Protocol](https://github.com/UiPath/uipath-runtime-python).

## Integrations

### LlamaIndex

[![PyPI - Version](https://img.shields.io/pypi/v/uipath-llamaindex)](https://pypi.org/project/uipath-llamaindex/)
[![PyPI downloads](https://img.shields.io/pypi/dm/uipath-llamaindex.svg)](https://pypi.org/project/uipath-llamaindex/)

Build agents using the [LlamaIndex SDK](https://www.llamaindex.ai/):

- [Docs](https://uipath.github.io/uipath-python/llamaindex/quick_start/)
- [Samples](packages/uipath-llamaindex/samples/)

### OpenAI Agents

[![PyPI - Version](https://img.shields.io/pypi/v/uipath-openai-agents)](https://pypi.org/project/uipath-openai-agents/)
[![PyPI downloads](https://img.shields.io/pypi/dm/uipath-openai-agents.svg)](https://pypi.org/project/uipath-openai-agents/)

Build agents using the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python):

- [Docs](https://uipath.github.io/uipath-python/openai-agents/quick_start/)
- [Samples](packages/uipath-openai-agents/samples/)


## Structure

This repository is organized as a monorepo with multiple packages:

```
uipath-integrations-python/
└── packages/
    ├── uipath-llamaindex/      # LlamaIndex runtime
    └── uipath-openai-agents/   # OpenAI Agents runtime
```

## Development

### Tools

Check out [uipath-dev](https://github.com/uipath/uipath-dev-python) - an interactive terminal application for building, testing, and debugging UiPath Python runtimes, agents, and automation scripts.

### Contributions

Please read our [contribution guidelines](https://github.com/UiPath/uipath-integrations-python/blob/main/CONTRIBUTING.md) before submitting a pull request.


