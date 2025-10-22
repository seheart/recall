# Contributing to Recall

Thanks for your interest in contributing to Recall! 🎉

## How to Contribute

### Reporting Bugs

Found a bug? Please [open an issue](https://github.com/seheart/recall/issues) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version)

### Suggesting Features

Have an idea? [Open an issue](https://github.com/seheart/recall/issues) with:
- Clear description of the feature
- Use case / problem it solves
- Any implementation ideas (optional)

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Install dev dependencies**: `pip install -r requirements-dev.txt`
3. **Set up pre-commit hooks** (optional but recommended): `pre-commit install`
4. **Make your changes** with clear, descriptive commits
5. **Add tests** if applicable (see `tests/` directory)
6. **Run tests**: `pytest tests/ -v --cov=recall_lib`
7. **Check linting**: `flake8 .`
8. **Format code**: `black .`
9. **Run type checking**: `mypy recall.py recall_lib/ --ignore-missing-imports`
10. **Submit PR** with clear description of changes

**Note:** All pull requests automatically run CI/CD checks (tests, linting, formatting) via GitHub Actions. Your PR must pass all checks before merging.

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/recall.git
cd recall

# Install dev dependencies
pip install -r requirements-dev.txt

# (Optional) Set up pre-commit hooks for automatic code quality checks
pre-commit install

# Run tests with coverage
pytest tests/ -v --cov=recall_lib --cov-report=term

# Check linting
flake8 .

# Format code with black
black .

# Run type checking
mypy recall.py recall_lib/ --ignore-missing-imports

# Or run all pre-commit hooks manually
pre-commit run --all-files
```

## Code Style

- **Type hints**: Use type hints for all functions
- **Docstrings**: Add docstrings for public functions
- **Error handling**: Use specific exception types (not bare `except:`)
- **Formatting**: Use `black` for consistent formatting (line length: 100)
- **Linting**: Follow flake8 rules (max complexity: 10)
- **Testing**: Add tests for new features (aim for >80% coverage)

## CI/CD Pipeline

All pull requests and commits to `main`/`develop` branches automatically run:

1. **Tests** - pytest across Python 3.9, 3.10, 3.11, 3.12, 3.13
2. **Linting** - flake8 checks for code quality and style
3. **Formatting** - black checks code formatting
4. **Type Checking** - mypy validates type hints (non-blocking)
5. **Coverage** - pytest-cov generates coverage reports

The CI/CD configuration is in `.github/workflows/test.yml`.

## Project Structure

```
recall/
├── recall.py              # Main CLI entry point
├── recall_lib/            # Core library modules
│   ├── database.py        # SQLite database management
│   ├── project_memory.py  # High-level memory API
│   ├── auto_analyzer.py   # Tech stack detection
│   └── ...
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## Questions?

Feel free to [open a discussion](https://github.com/seheart/recall/discussions) or ask in an issue!

---

Built with ❤️ by the community
