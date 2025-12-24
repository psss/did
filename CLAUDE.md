# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`did` is a command-line tool for gathering status report data from various development tools and services. It queries APIs (Jira, GitHub, GitLab, Bugzilla, etc.) and local repositories to summarize what a user accomplished in a given time period.

## Common Development Commands

### Testing
```bash
# Run all tests in parallel
make test

# Run smoke tests (CLI tests only)
make smoke

# Run tests with coverage
make coverage

# Run functional tests (requires --functional flag and online resources)
pytest --functional tests/

# Run a single test file
DID_DIR=tmp pytest tests/test_cli.py

# Run a specific test
DID_DIR=tmp pytest tests/plugins/test_jira.py::test_config_gss_auth
```

**Note**: Tests require `DID_DIR` environment variable set to a temporary directory. The `make test` target handles this automatically.

### Code Quality
```bash
# Install pre-commit hooks
make hooks

# Run all pre-commit checks manually
pre-commit run --all-files

# Run specific linters
flake8          # Style checking (max line length: 88)
pylint          # Code analysis
mypy            # Type checking
codespell       # Spell checking
```

### Documentation
```bash
# Build HTML documentation
make docs

# Build man page
make man
```

### Installation & Packaging
```bash
# Install in development mode
pip install -e .

# Install with specific plugin dependencies
pip install -e .[jira]
pip install -e .[all]

# Build RPM package
make rpm

# Build Python wheel
make wheel
```

## Architecture

### Plugin System

The core architecture is built around a plugin system where each plugin represents a different tool/service (Jira, GitHub, Bugzilla, etc.).

**Key components:**

- **`did/base.py`** - Core classes: `Config`, `Date`, `User`, and base exceptions
- **`did/stats.py`** - `Stats` and `StatsGroup` base classes that all plugins inherit from
- **`did/cli.py`** - Command-line argument parsing and main execution loop
- **`did/utils.py`** - Shared utilities: logging, plugin loading, color output
- **`did/plugins/`** - Individual plugin implementations

**Plugin structure:**
Each plugin module (e.g., `did/plugins/jira.py`) contains:
1. A main `StatsGroup` subclass (e.g., `JiraStats`) that groups related stats
2. Multiple `Stats` subclasses for different report types (e.g., `JiraCreated`, `JiraResolved`)
3. An `order` attribute defining position in the final report (see `did/plugins/__init__.py`)

**How plugins are loaded:**
- Plugins are auto-discovered from the `did/plugins/` directory
- Plugin name must match the `type` field in config sections
- Each plugin's `StatsGroup` adds its stats to the user report
- Custom plugins can be loaded by adding paths to the `[general]` section in config

### Configuration System

Configuration is read from `~/.did/config` (INI format):
- `[general]` section contains email, width, and other global settings
- Each plugin has its own section with `type = <plugin_name>`
- Plugins define their own config options (auth, URLs, filters, etc.)

### Stats Collection Flow

1. CLI parses arguments and loads configuration
2. `UserStats` (from `stats.py`) instantiates all enabled plugins
3. Each plugin's `fetch()` method queries its API/data source
4. Results are collected into the plugin's `stats` list
5. Output is formatted and displayed (text/markdown/wiki formats)

### Date Handling

The `Date` class in `did/base.py` provides flexible date parsing:
- Natural language: "today", "yesterday", "last week", "last friday"
- Explicit ranges: `--since YYYY-MM-DD --until YYYY-MM-DD`
- Period helpers: "this week", "last month", "this quarter", "last year"

### Testing Structure

- **Unit tests**: `tests/test_*.py` - Test core functionality
- **Plugin tests**: `tests/plugins/test_*.py` - Test individual plugins
- **Functional tests**: Marked with `@pytest.mark.functional` - Require `--functional` flag
- **Test configs**: Embedded in test files as strings, not external files
- **Fixtures**: Defined in `conftest.py` - Adds `--functional` option to pytest

## Type Hints

This codebase uses type hints and enforces them with mypy. When modifying code:
- Add type hints to new functions and methods
- Use `Optional[T]` for nullable values
- Import types from `typing` module as needed
- Plugin-specific types may require additional dependencies (see `setup.py` extras_require)

## Pre-commit Hooks

The project uses pre-commit with:
- `autopep8` - Auto-formatting (max line length: 88)
- `isort` - Import sorting
- `flake8` - Style enforcement
- `pylint` - Code analysis
- `mypy` - Type checking
- `codespell` - Spell checking

Changes must pass all checks before committing. Run `make hooks` to install them.

## Important Conventions

- **Error handling**: Plugins catch API errors in `Stats.check()` and set `self.error = True`
- **Logging**: Use `from did.utils import log` and appropriate levels (LOG_DEBUG, LOG_INFO, etc.)
- **Plugin order**: Defined by the `order` class attribute (see `did/plugins/__init__.py`)
- **Authentication**: Plugins support various auth types (GSS/Kerberos, token, basic auth)
- **Config validation**: Plugins validate required config in `__init__` and raise `ConfigError`
