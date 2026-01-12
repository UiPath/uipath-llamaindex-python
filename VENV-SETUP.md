# Virtual Environment Setup Guide

This repository is configured with individual virtual environments for each package.

## Structure

```
uipath-integrations-python/
├── packages/
│   ├── uipath-llamaindex/
│   │   ├── .venv/              # Virtual environment for llamaindex
│   │   ├── .vscode/            # Package-specific VSCode settings
│   │   └── pyproject.toml
│   └── uipath-openai-agents/
│       ├── .venv/              # Virtual environment for openai-agents
│       ├── .vscode/            # Package-specific VSCode settings
│       └── pyproject.toml
└── uipath-integrations.code-workspace  # Multi-root workspace
```

## VSCode Setup

### Option 1: Multi-Root Workspace (Recommended)

1. Open the workspace file:
   ```bash
   code uipath-integrations.code-workspace
   ```

2. VSCode will automatically detect and use the correct `.venv` for each package folder

3. Each package folder will appear as a separate root in the workspace, with its own interpreter

### Option 2: Individual Package Development

If you want to work on a single package:

1. Open the package directory directly:
   ```bash
   code packages/uipath-llamaindex
   # or
   code packages/uipath-openai-agents
   ```

2. Select the interpreter:
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Python: Select Interpreter"
   - Choose `./.venv/bin/python`

## Virtual Environment Management

### Create/Recreate Virtual Environments

For **uipath-llamaindex**:
```bash
cd packages/uipath-llamaindex
uv venv .venv
uv sync --all-extras
```

For **uipath-openai-agents**:
```bash
cd packages/uipath-openai-agents
uv venv .venv
uv sync --all-extras
```

### Activate Virtual Environments (Terminal)

For **uipath-llamaindex**:
```bash
source packages/uipath-llamaindex/.venv/bin/activate
```

For **uipath-openai-agents**:
```bash
source packages/uipath-openai-agents/.venv/bin/activate
```

### Verify Active Interpreter

```bash
which python
python --version
```

## Benefits of This Setup

1. **Isolation**: Each package has its own dependencies without conflicts
2. **Clarity**: Easy to see which package you're working on
3. **IDE Integration**: VSCode automatically uses the correct interpreter per package
4. **Testing**: Run tests with the exact dependencies for that package
5. **Development**: Install dev dependencies independently per package

## Common Commands Per Package

From within each package directory:

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Type checking
uv run mypy --config-file pyproject.toml .

# Linting
uv run ruff check .

# Formatting
uv run ruff format .
```

## Troubleshooting

### VSCode Not Using Correct Interpreter

1. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Run "Python: Select Interpreter"
3. Choose the `.venv/bin/python` option for the current package

### Virtual Environment Not Found

Recreate it:
```bash
cd packages/<package-name>
uv venv .venv --clear
uv sync --all-extras
```

### Dependencies Out of Sync

```bash
cd packages/<package-name>
uv sync --all-extras --reinstall
```
