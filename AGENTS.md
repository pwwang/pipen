# AGENTS.md

This file contains development guidelines for agentic coding agents working on this repository.

## Build/Lint/Test Commands

```bash
# Installation
poetry install --all-extras

# Build package
poetry build

# Format code (Black, line-length=88)
black pipen

# Check formatting without changes
black --check pipen

# Lint code (flake8)
flake8 pipen

# Type checking (mypy)
mypy -p pipen

# Run all tests (pytest with parallel execution)
pytest tests/

# Run single test file
pytest tests/test_proc.py

# Run specific test
pytest tests/test_proc.py::test_proc_no_input

# Run tests with coverage
pytest --cov=pipen --cov-report=term-missing

# Run tests for single file with coverage
pytest tests/test_proc.py --cov=pipen --cov-report=term-missing

# Run with verbose output
pytest -vv tests/

# Run documentation build
cd docs && mkdocs build
```

## Code Style Guidelines

### Imports
1. Use `from __future__ import annotations` at the top of all Python files
2. Import order: standard library → third-party → local modules
3. Use `if TYPE_CHECKING:` blocks for circular imports and type-only imports

```python
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from diot import Diot
from rich import box

from .defaults import ProcInputType
from .exceptions import ProcInputKeyError

if TYPE_CHECKING:
    from .pipen import Pipen
```

### Type Hints
- Use type hints for all public functions and methods
- Use modern Python 3.9+ union syntax (`x | None` instead of `Optional[x]`)
- Use `TYPE_CHECKING` to avoid import cycles
- Use `Dict`, `List`, `Tuple` from typing module for compatibility

### Naming Conventions
- **Classes**: `CamelCase` (e.g., `Proc`, `Pipen`, `ProcGroup`)
- **Functions/Methods**: `snake_case` (e.g., `get_scheduler`, `run_pipeline`)
- **Variables**: `snake_case` (e.g., `input_data`, `output_file`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `LOGGER_NAME`, `MAX_RETRIES`)
- **Private members**: single underscore prefix (e.g., `_compute_requires`)

### Docstrings
Use **Google-style** docstrings with Args, Returns, Raises, and Attributes sections:

```python
def process_data(input_file: str, output_dir: str, verbose: bool = False) -> dict:
    """Process a data file and save results.

    Args:
        input_file: Path to the input data file.
        output_dir: Directory where results will be saved.
        verbose: If True, print detailed progress.

    Returns:
        Dictionary containing processing statistics.

    Raises:
        FileNotFoundError: If input_file does not exist.
    """
```

### Error Handling
- Define custom exceptions in `pipen/exceptions.py`
- Raise descriptive error messages with context
- Use appropriate exception types from built-ins and custom exceptions
- Include relevant variable names and values in error messages

```python
if not isinstance(inval, (str, Path)):
    msg = (
        f"[{proc_name}] Got <{type(inval).__name__}> instead of "
        f"path-like object for input: {inkey + ':' + intype!r}"
    )
    raise ProcInputTypeError(msg)
```

### Formatting
- Line length: 88 characters (Black default)
- Use Black formatter: `black pipen`
- No trailing whitespace
- End files with newline

### Type Checking (mypy)
- Ignore missing imports from external packages
- Allow redefinition in some cases (`attr-defined`, `no-redef`)
- Strict optional mode is disabled
- Run `mypy -p pipen` before committing

### Test Patterns
- Test files: `tests/test_*.py`
- Use `@pytest.mark.forked` for isolated process tests
- Use `@pytest.mark.asyncio` for async tests
- Test functions: `test_*`
- Fixtures defined in `tests/conftest.py`
- Parallel execution with `pytest-xdist` (`-n auto`)

### Linting (flake8)
- Ignore: `E203`, `W503` (conflicts with Black)
- Per-file ignores:
  - `__init__.py: F401` (imported but unused)
  - `tests/*: F811` (redefinition of fixtures)
- Max line length: 88

### Pre-commit Hooks
Pre-commit hooks automatically run on commit for files in `pipen/` directory:
- trailing-whitespace
- end-of-file-fixer
- check-yaml
- check-added-large-files
- mypy
- pytest
- flake8

Install hooks: `pre-commit install`

## Project Structure
- `pipen/`: Main package directory
- `tests/`: Test files mirroring package structure
- `examples/`: Example pipelines
- `docs/`: Documentation (MkDocs)

## Notes for Agents
- Always run tests before finalizing changes: `pytest tests/`
- Use `mypy -p pipen` to ensure type safety
- Follow existing patterns in the codebase for consistency
- The project uses Poetry for dependency management
- Check `CONTRIBUTING.md` for detailed development guidelines
