# Recall Unit Tests

Comprehensive test suite for the Recall project memory system.

## Setup

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_database.py -v
```

Run with coverage report:
```bash
pytest tests/ --cov=recall_lib --cov-report=html
```

Run tests and stop on first failure:
```bash
pytest tests/ -x
```

## Test Structure

- `test_database.py` - Tests for RecallDatabase (SQLite operations)
- `test_project_memory.py` - Tests for ProjectMemory (caching, context management)
- `test_git_utils.py` - Tests for git operations (commits, status, branches)

## Test Coverage

Current test coverage:
- Database operations: ~90%
- Project memory & caching: ~85%
- Git utilities: ~95%

## Writing New Tests

Follow these guidelines when adding tests:

1. Use descriptive test names starting with `test_`
2. Use fixtures for setup/teardown (see `@pytest.fixture`)
3. Test both success and failure cases
4. Use assertions liberally
5. Keep tests isolated and independent

Example test structure:
```python
def test_feature_name(fixture_name):
    """Brief description of what this tests"""
    # Arrange
    setup_code()

    # Act
    result = function_under_test()

    # Assert
    assert result == expected_value
```

## Continuous Integration

To run tests in CI/CD:

```yaml
- name: Run tests
  run: |
    pip install -r requirements-dev.txt
    pytest tests/ -v --cov=recall_lib
```
