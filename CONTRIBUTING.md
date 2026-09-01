# Contributing

Contributions to `command_creator` are welcome. This guide covers how to set up a
development environment, run the test suite, and open a pull request.

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) package manager

## Getting Setup

`command_creator` uses [`uv`](https://docs.astral.sh/uv/) as its packaging and
tool-running utility, and [`tox`](https://tox.wiki/) (via `tox-uv`) to orchestrate the
test, style, typing, and docs environments.

### Installing uv

- **Linux/Mac**: `pip install uv`, or via your system package manager
- **Windows**: download from the [uv releases](https://github.com/astral-sh/uv/releases)

### Syncing the environment

```bash
uv sync            # Create the virtual environment and install all dependencies
```

## Development Workflow

The quickest way to run every check is `tox`, which runs the unit tests, style checks,
type checks, and documentation build in one command:

```bash
uv run tox         # Run all environments (py314, style, typing, docs_dirhtml)
uv run tox -p      # Run environments in parallel (faster)
```

You can also run each environment individually.

### Testing - pytest

Unit tests live in the `./tests/` directory.

```bash
uv run tox -e py314                                # Run the test suite
uv run pytest                                      # Run pytest directly
uv run pytest tests/test_module.py::test_function  # Run a single test
```

### Code Quality - ruff

`ruff` enforces style (PEP 8) and catches common bugs.

```bash
uv run tox -e style        # Run the style checks
uv run ruff check          # Check code style directly
uv run ruff check --fix    # Auto-fix style issues
uv run ruff format         # Format code
```

### Type Checking - mypy

```bash
uv run tox -e typing       # Run the type checks
uv run mypy                # Run mypy directly
```

### Documentation - Sphinx

The documentation is built with Sphinx (warnings are treated as errors).

```bash
uv run tox -e docs_dirhtml # Build the HTML docs into docs/_build/dirhtml
```

Open `docs/_build/dirhtml/index.html` in a browser to preview.

## Code Formatting Guidelines

All Python code must comply with [PEP 8](https://peps.python.org/pep-0008/). Project
settings are configured in `pyproject.toml`:

- Line length: 100 characters
- Target Python version: 3.14
- Quote style: double quotes
- Import sorting: enabled (`command_creator` is treated as first-party)

## Branching and Commit Conventions

### Branch Naming

- `feature/*` - New features (e.g. `feature/add-completer`)
- `bugfix/*` - Bug fixes (e.g. `bugfix/enum-choices`)
- `docs/*` - Documentation updates
- `chore/*` - Maintenance tasks

### Commit Messages

```
(BREAKING) description

Optional body with more details
```

Prefix the subject with `(BREAKING)` only for changes that require a major version bump.

## Before Opening a Pull Request

Ensure all of the following are complete:

- [ ] All checks pass: `uv run tox` (or `uv run tox -p`)
    - [ ] Tests pass: `uv run tox -e py314`
    - [ ] Style is clean: `uv run ruff check --fix`
    - [ ] Type checking passes: `uv run tox -e typing`
    - [ ] Docs build: `uv run tox -e docs_dirhtml`
- [ ] `CHANGELOG.md` updated with your changes under the in-progress version
- [ ] Documentation updated (docstrings, `README.md`, `docs/`) where relevant
- [ ] Branch follows the naming convention above
- [ ] PR description explains the change and its motivation

## Troubleshooting

### `uv` command not found

- Ensure `uv` is installed and on your `PATH`
- Try `python -m pip install uv`

### Import errors when running tests

- Run commands through `uv run` rather than invoking tools directly
- Try `uv sync` to refresh the environment

### Tests pass locally but fail in CI

- Run the full suite with `uv run tox`, not just `pytest`
- Confirm your Python version: `python --version` (must be 3.14+)

## License

By contributing, you agree that your contributions are licensed under the project's
[GNU Lesser General Public License v2.1 or later](https://github.com/allRisc/command_creator/blob/main/LICENSE).
