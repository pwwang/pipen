# Contributing to pipen

Thank you for your interest in contributing to pipen! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- Git

### Setting Up the Development Environment

1. **Fork and clone the repository**

   ```bash
   # Fork the repository on GitHub first
   git clone https://github.com/YOUR_USERNAME/pipen.git
   cd pipen
   ```

2. **Install development dependencies**

   ```bash
   # Install using Poetry
   poetry install --all-extras

   # Or install the development group specifically
   poetry install --with dev,docs,example
   ```

3. **Activate the virtual environment**

   ```bash
   # Using Poetry shell
   poetry shell

   # Or use the virtual environment path
   source $(poetry env info --path)/bin/activate
   ```

4. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Verify the setup**

   ```bash
   # Run tests to ensure everything is working
   pytest tests/

   # Build documentation
   cd docs && mkdocs build
   ```

### Development Workflow

```bash
# Create a new branch for your changes
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Run tests
pytest tests/

# Run linting
flake8 pipen
mypy -p pipen

# Format code
black pipen

# Commit changes
git add .
git commit -m "Add your feature"

# Push to your fork
git push origin feature/your-feature-name
```

## Code Style

### Formatting

We use [Black](https://black.readthedocs.io/) for code formatting:

```bash
# Format code
black pipen

# Check formatting without making changes
black --check pipen
```

Configuration:
- Line length: 88 characters
- Target Python versions: 3.9, 3.10, 3.11, 3.12

### Linting

We use [flake8](https://flake8.pycqa.org/) for code linting:

```bash
flake8 pipen
```

### Type Checking

We use [mypy](https://mypy.readthedocs.io/) for static type checking:

```bash
mypy -p pipen
```

Configuration:
- Ignore missing imports from external packages
- Allow redefinition in some cases
- Strict optional mode is disabled for flexibility

### Docstring Format

We use **Google-style docstrings** with Args, Returns, Raises, and Attributes sections:

```python
def process_data(input_file: str, output_dir: str, verbose: bool = False) -> dict:
    """Process a data file and save results to output directory.

    This function reads the input file, processes the data, and saves
    the results to the specified output directory.

    Args:
        input_file: Path to the input data file.
        output_dir: Directory where processed results will be saved.
        verbose: If True, print detailed progress information.

    Returns:
        Dictionary containing processing statistics and output file paths.

    Raises:
        FileNotFoundError: If input_file does not exist.
        ValueError: If input_file is malformed.

    Examples:
        >>> result = process_data("data.csv", "output")
        >>> result['processed_count']
        100
    """
    pass
```

For classes, include a description and list important attributes:

```python
class DataProcessor:
    """Process and transform data files.

    This class provides methods for reading, transforming, and saving
    data in various formats.

    Attributes:
        processed_count: Number of files processed.
        errors: List of errors encountered during processing.
        config: Configuration dictionary for processing parameters.
    """
    pass
```

### Pre-commit Hooks

We use pre-commit hooks to automatically run checks before committing:

- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with a newline
- **check-yaml**: Validate YAML syntax
- **check-added-large-files**: Prevent large files from being committed
- **versionchecker**: Ensure version consistency between `pyproject.toml` and `pipen/version.py`
- **mypy**: Run type checking
- **pytest**: Run tests
- **flake8**: Run linting

Pre-commit hooks are configured in `.pre-commit-config.yaml` and automatically
run on commits for files in `pipen/` directory (excludes `tests/`, `examples/`, and `docs/`).

## Testing

### Running Tests

We use [pytest](https://docs.pytest.org/) for testing:

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=pipen --cov-report=term-missing

# Run specific test file
pytest tests/test_pipen.py

# Run with verbose output
pytest -vv tests/

# Run specific test
pytest tests/test_pipen.py::test_pipen_init
```

### Test Configuration

Our test configuration (from `pyproject.toml`):

- **Parallel execution**: `pytest-xdist` with `-n auto` for automatic parallelization
- **Distribution mode**: `--dist loadgroup` to run dependent tests together
- **Coverage**: `pytest-cov` for code coverage reporting
- **Async support**: `pytest-asyncio` for async test cases
- **Warnings**: Treat `UserWarning` as errors (`-W error::UserWarning`)

### Writing Tests

Place tests in the `tests/` directory following the structure:

```python
# tests/test_pipen.py
import pytest
from pipen import Pipen, Proc

def test_pipen_init():
    """Test that Pipen initializes correctly."""
    pipeline = Pipen()
    assert pipeline.name == "Pipen"

@pytest.mark.asyncio
async def test_async_pipeline():
    """Test async pipeline execution."""
    pipeline = Pipen()
    result = await pipeline.run_async()
    assert result is True
```

### Test Coverage

We aim for high test coverage. The current coverage is tracked on [Codacy](https://app.codacy.com/gh/pwwang/pipen).

To check coverage locally:

```bash
pytest --cov=pipen --cov-report=html
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Documentation

### Building Documentation

Documentation is built with [MkDocs](https://www.mkdocs.org/):

```bash
cd docs
mkdocs build        # Build to site/
mkdocs serve        # Serve at http://127.0.0.1:8000
mkdocs gh-deploy    # Deploy to GitHub Pages
```

### Documentation Structure

```
docs/
├── index.md              # Symlink to ../README.md
├── basics.md             # Pipeline layers and folder structure
├── defining-proc.md      # Process definition guide
├── running.md            # Pipeline execution guide
├── configurations.md     # Configuration documentation
├── caching.md            # Job caching mechanism
├── channels.md           # Channel system documentation
├── input-output.md      # Input/output specification
├── error.md             # Error handling strategies
├── templating.md        # Template engine documentation
├── script.md            # Script configuration
├── scheduler.md         # Scheduler backends
├── cloud.md             # Cloud support
├── proc-group.md        # Process groups
├── plugin.md            # Plugin development
├── cli.md               # CLI tool documentation
├── examples.md          # Example documentation
├── CHANGELOG.md         # Version history
├── style.css            # Custom styling
└── script.js            # Custom JavaScript
```

### API Documentation

API documentation is auto-generated from docstrings using the `mkapi-fix` plugin.

To ensure your API documentation is properly generated:

1. Write Google-style docstrings for all public classes, functions, and methods
2. Include `Args`, `Returns`, `Raises`, and `Attributes` sections where applicable
3. Add `Examples` sections for complex functions
4. Ensure type hints are present in function signatures

### Adding New Documentation

1. Create a new `.md` file in the `docs/` directory
2. Update the `nav` section in `mkdocs.yml` to include your new page
3. Add cross-references using `[](#anchor)` syntax
4. Use code blocks with language identifiers: ```python, ```bash, etc.
5. Use admonition blocks for notes, warnings, and tips:

   ```markdown
   !!! note
       This is a note block.

   !!! warning
       This is a warning.

   !!! tip
       This is a tip.
   ```

### Documentation Requirements

- All new public APIs must have docstrings
- Breaking changes must be documented in `CHANGELOG.md`
- New features should include examples in the documentation
- Visual diagrams should have descriptive alt text for accessibility

## Pull Request Process

### Before Submitting a PR

1. **Update documentation**
   - Add or update docstrings for changed code
   - Update relevant documentation files
   - Add examples for new features

2. **Run all tests**
   ```bash
   pytest tests/
   ```

3. **Run linting and type checking**
   ```bash
   flake8 pipen
   mypy -p pipen
   black --check pipen
   ```

4. **Build documentation**
   ```bash
   cd docs && mkdocs build
   ```

5. **Update CHANGELOG.md**
   - Add an entry under the appropriate version section
   - Use the format: `[<type>] <description> ([#issue])`
   - Types: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`

### Submitting a PR

1. Push your branch to your fork
2. Open a pull request on GitHub
3. Fill in the PR template with:
   - A clear description of changes
   - Related issues (if any)
   - Screenshots for UI changes (if applicable)
   - Testing performed
   - Documentation updates

### PR Review Process

- Maintainers will review your PR
- Address review comments by pushing additional commits
- Keep the PR focused on a single change
- Squash commits if requested by maintainers
- Update based on review feedback

### Merge Criteria

A PR can be merged when:

- [ ] All tests pass
- [ ] Code is properly formatted (Black)
- [ ] No linting errors (flake8)
- [ ] No type checking errors (mypy)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated for breaking changes
- [ ] At least one maintainer approves

## Reporting Issues

### Bug Reports

When reporting a bug, include:

1. **Python version**: `python --version`
2. **pipen version**: `pipen --version`
3. **Minimal reproducible example**: Code that demonstrates the issue
4. **Expected behavior**: What you expected to happen
5. **Actual behavior**: What actually happened (with error messages)
6. **Environment details**: OS, scheduler used, etc.

### Feature Requests

When requesting a feature:

1. **Use case**: Explain what problem this feature solves
2. **Proposed solution**: How you envision the feature working
3. **Alternatives considered**: Other approaches you've thought of
4. **Additional context**: Any relevant context about the request

### Documentation Issues

For documentation issues:

1. **Page location**: Which documentation page has the issue
2. **Problem**: What is incorrect, unclear, or missing
3. **Suggestion**: How it should be improved (if you have ideas)

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: https://pwwang.github.io/pipen
- **Examples**: See the `examples/` directory for usage examples

## License

By contributing to pipen, you agree that your contributions will be licensed under the MIT License.
