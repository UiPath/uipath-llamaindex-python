# UiPath AI Agent Runtimes for Python

A collection of Python SDKs that enable developers to build and deploy AI agents to the UiPath Cloud Platform using different agent frameworks. These packages provide programmatic interaction with UiPath Cloud Platform services and human-in-the-loop (HITL) semantics through Action Center integration.

All packages are extensions to the [UiPath Python SDK](https://github.com/UiPath/uipath-python) and implement the [UiPath Runtime Protocol](https://github.com/UiPath/uipath-runtime-python).

## Available Packages

### UiPath LlamaIndex

[![PyPI - Version](https://img.shields.io/pypi/v/uipath-llamaindex)](https://pypi.org/project/uipath-llamaindex/)
[![PyPI downloads](https://img.shields.io/pypi/dm/uipath-llamaindex.svg)](https://pypi.org/project/uipath-llamaindex/)

Build agents using the [LlamaIndex](https://www.llamaindex.ai/) framework with support for RAG, multiple LLM providers, and state persistence.

- **Installation**: `pip install uipath-llamaindex`
- **Documentation**: [packages/uipath-llamaindex/](packages/uipath-llamaindex/)
- **Samples**: [packages/uipath-llamaindex/samples/](packages/uipath-llamaindex/samples/)

### UiPath OpenAI Agents

[![PyPI - Version](https://img.shields.io/pypi/v/uipath-openai-agents)](https://pypi.org/project/uipath-openai-agents/)

Build agents using [OpenAI's native Agents framework](https://platform.openai.com/docs/agents) for multi-agent coordination.

- **Installation**: `pip install uipath-openai-agents`
- **Documentation**: [packages/uipath-openai-agents/](packages/uipath-openai-agents/)
- **Status**: ⚠️ Early development (v0.1.0)

## Requirements

-   Python 3.11 or higher
-   UiPath Automation Cloud account

## Quick Start

Choose the agent framework that best fits your needs and follow the installation instructions for that package:

- **LlamaIndex**: For RAG applications and stateful workflows → See [LlamaIndex documentation](packages/uipath-llamaindex/)
- **OpenAI Agents**: For multi-agent systems → See [OpenAI Agents documentation](packages/uipath-openai-agents/)

## Documentation

- [Quick Start Guide](docs/quick_start.md)
- [LlamaIndex Package Documentation](packages/uipath-llamaindex/)
- [OpenAI Agents Package Documentation](packages/uipath-openai-agents/)
- [Sample Projects](packages/uipath-llamaindex/samples/)

## Monorepo Structure

This repository is organized as a UV workspace with multiple packages:

```
uipath-llamaindex-python/
├── packages/
│   ├── uipath-llamaindex/      # LlamaIndex runtime
│   └── uipath-openai-agents/   # OpenAI Agents runtime
├── docs/                        # Shared documentation
└── pyproject.toml              # Workspace configuration
```

## Development

### Setting Up a Development Environment

This repository uses [UV](https://docs.astral.sh/uv/) for workspace management:

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/UiPath/uipath-llamaindex-python.git
cd uipath-llamaindex-python

# Install all dependencies
uv sync --all-extras

# Run tests for all packages
uv run pytest

# Build a specific package
uv build --package uipath-llamaindex
uv build --package uipath-openai-agents
```

### Developer Tools

Check out [uipath-dev](https://github.com/uipath/uipath-dev-python) - an interactive terminal application for building, testing, and debugging UiPath Python runtimes, agents, and automation scripts.

### Contributing

Please read our [contribution guidelines](CONTRIBUTING.md) before submitting a pull request.

## Special Thanks

A huge thank-you to the open-source community and the maintainers of the libraries that make this project possible:

- [LlamaIndex](https://github.com/run-llama/llama_index) for providing a powerful framework for building stateful LLM applications
- [OpenAI](https://github.com/openai) for the Agents framework and APIs
- [OpenInference](https://github.com/Arize-ai/openinference) for observability and instrumentation support
- [Pydantic](https://github.com/pydantic/pydantic) for reliable, typed configuration and validation

## License

See [LICENSE](LICENSE) for details.
