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
3. **Make your changes** with clear, descriptive commits
4. **Add tests** if applicable (see `tests/` directory)
5. **Run tests**: `pytest`
6. **Run type checking**: `mypy recall_lib/`
7. **Format code**: `black .`
8. **Submit PR** with clear description of changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/recall.git
cd recall

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run type checking
mypy recall_lib/

# Format code
black .
```

## Code Style

- **Type hints**: Use type hints for all functions
- **Docstrings**: Add docstrings for public functions
- **Error handling**: Use specific exception types (not bare `except:`)
- **Formatting**: Use `black` for consistent formatting
- **Testing**: Add tests for new features

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
