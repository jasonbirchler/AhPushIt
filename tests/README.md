# Test Suite

This directory contains the test suite for the Pysha project.

## Running Tests

### Install test dependencies

```bash
pip install -r requirements-dev.txt
```

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=.
```

### Run only unit tests

```bash
pytest -m unit
```

### Run only integration tests

```bash
pytest -m integration
```

### Run simulator tests (requires Push2 simulator to be running)

```bash
pytest -m simulator
```

### Run slow tests

```bash
pytest -m slow
```

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_definitions.py      # Tests for definitions module
├── test_utils.py           # Tests for utils module
├── test_base_class.py      # Tests for base_class module
├── test_session.py         # Tests for session module
├── test_track.py           # Tests for track module
├── test_sequencer.py       # Tests for sequencer module
├── test_clip.py            # Tests for clip module
└── modes/                  # Tests for mode classes
    ├── test_pyshamode.py
    ├── test_melodic_mode.py
    ├── test_rhythmic_mode.py
    ├── test_clip_triggering_mode.py
    ├── test_clip_edit_mode.py
    ├── test_track_selection_mode.py
    ├── test_preset_selection_mode.py
    ├── test_midi_cc_mode.py
    ├── test_settings_mode.py
    ├── test_main_controls_mode.py
    ├── test_add_track_mode.py
    └── test_slice_notes_mode.py
```

## Markers

Tests are marked with the following categories:

- `unit` - Fast, isolated unit tests with minimal dependencies
- `integration` - Tests that exercise multiple components together
- `simulator` - Tests that use the Push2 simulator (requires simulator running)
- `slow` - Tests that take significant time (>1s)
- `hardware` - Tests that require actual Push2 hardware

## Writing Tests

### Use fixtures

The `conftest.py` provides many useful fixtures:

- `mock_push2_environment` - Mocks the Push2 hardware interface
- `mock_app` - Provides a mock PyshaApp instance
- `mock_cairo_context` - Provides a mock cairo drawing context
- `track_selection_mode`, `melodic_mode`, etc. - Common mode instances
- `session`, `track`, `sequencer` - Core components

Example:

```python
def test_something(mock_app, melodic_mode):
    # Use fixtures
    result = melodic_mode.some_method()
    assert result is not None
```

### Mock external dependencies

Use `unittest.mock` or `pytest-mock` to mock:
- MIDI devices
- File system operations
- Network calls

### Test structure

Follow this pattern:

```python
class TestFeatureName:
    """Description of what's being tested."""
    
    def test_basic_functionality(self, mock_app):
        """Test brief description."""
        # Arrange
        mode = FeatureMode(mock_app)
        
        # Act
        result = mode.method_under_test()
        
        # Assert
        assert result == expected
```

## Continuous Integration

The GitHub Actions CI pipeline (`.github/workflows/ci.yml`) runs:

1. Installation of dependencies
2. Unit tests with coverage
3. Type checking (if configured)
4. Code formatting checks (if configured)

All tests must pass before merging to `main`.

## Coverage

Current coverage threshold: 80%

To view coverage report:

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```
