# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`did` is a Python CLI that gathers status-report data ("What did you do last week, month, year?") by querying many issue/code-review/wiki backends and aggregating the results into a single report. Distributed as a Python package and as Fedora/EPEL RPMs (via `did.spec` + Packit).

## Common commands

Tests use a temp `DID_DIR` and run in parallel (`pytest-xdist`). The `Makefile` wires the canonical invocations:

- `make test` — full suite (`pytest -n auto tests`)
- `make smoke` — fast CLI smoke (`tests/test_cli.py`)
- `make coverage` — coverage to `cov_html/`
- Single test: `DID_DIR=$(mktemp -d) pytest tests/unit/test_stats.py::TestStatsGroup::test_name -n0`
- Lint/format (matches CI): `pre-commit run --all-files` — runs autopep8, isort, flake8 (with `flake8-pytest-style`), pylint, codespell, mypy, and assorted file hooks. Config in `.pre-commit-config.yaml`.
- Install dev extras: `pip install -e '.[all]'` (or pick a backend extra: `bugzilla`, `jira`, `google`, `koji`, `redmine`, `rt`, `nitrate`, `bodhi`, `tests`, `mypy`, `docs`).
- Docs: `make docs` (Sphinx, also built on Read the Docs via `.readthedocs.yaml`).
- RPM: `make rpm` / `make srpm` (uses `did.spec`; Packit config in `.packit.yaml`).
- Version: parsed by `setup.py` from `did.spec`'s `Version:` and `Release:` lines — bump there, not in `setup.py`.

## Architecture

Three layers, all rooted in `did/`:

1. **CLI + config (`did/cli.py`, `did/base.py`)** — `cli.py` parses args and orchestrates the run. `base.py` owns the `Config`, `Date`, and `User` objects plus the date-range arithmetic (`this/last week|month|quarter|year`, `WEEKDAY_MAP`, etc.). Config comes from `~/.did/config` (override with `DID_DIR` / `DID_CONFIG`) and is sectioned: a `[general]` section sets defaults; every other section is one plugin instance whose `type = <plugin_name>` selects the backend.

2. **Stats core (`did/stats.py`)** — defines `Stats` and `StatsGroup`. A `StatsGroup` is the per-config-section container; `Stats` subclasses are the individual queries (e.g. "issues created"). `UserStats` fans groups out across configured users. Plugin work runs through a `ThreadPoolExecutor`, so plugin code must be thread-safe and surface its own errors (`Stats.error`) rather than crashing the run.

3. **Plugins (`did/plugins/*.py`)** — one file per backend (Jira, Bugzilla, GitHub, GitLab, Gerrit, Koji, Bodhi, Google, Confluence, Sentry, Trello, Pagure, Forgejo, Phabricator, Redmine, RT, Trac, Nitrate, Hyperkitty, public-inbox, git, wiki, plus `header`/`footer`). Each plugin defines a `StatsGroup` subclass and one or more `Stats` subclasses; the plugin module is loaded by name from the config's `type = ...`. Backend-specific extras live in `setup.py`'s `extras_require` — keep the two in sync when adding a plugin.

### Adding a plugin

Create `did/plugins/<name>.py` with a `<Name>Stats(StatsGroup)` plus the individual `Stats` subclasses, mirror the structure of a similar existing plugin (e.g. `github.py` for REST, `jira.py` for auth-heavy, `git.py` for local), add any new third-party dep to `extras_require` in `setup.py`, document the config section in `docs/plugins/`, and add unit coverage under `tests/unit/plugins/`.

## Tests

- `tests/unit/` — pure unit tests (`test_base.py`, `test_cli.py`, `test_stats.py`, `test_utils.py`, `plugins/`). These are what runs in the GitHub Actions `pre-commit.yml` / unit workflow.
- `tests/basic/` and the FMF metadata (`*.fmf`, `.fmf/`, `plans/`) drive `tmt`-based integration tests run downstream in Testing Farm via Packit — not part of `pytest`. Don't add Python tests under `tests/basic/`.
- `conftest.py` and `pytest.ini` set the shared fixtures and discovery rules.

## Conventions worth knowing

- Style is enforced by pre-commit (autopep8 `--aggressive --aggressive --max-line-length=88`, isort, flake8). Don't hand-format; let the hook do it.
- Python 3.9+ is supported (see classifiers in `setup.py`); type hints use `Optional[...]` and `from __future__ import annotations` is used selectively — match the file you're editing.
- Logging goes through `did.utils.log`; user-facing output uses the report formatter, not `print`.
- Network/credentials in plugins: read tokens via `token_file` config keys (see existing plugins) rather than embedding them; GSSAPI is used for several Red Hat-internal backends.
