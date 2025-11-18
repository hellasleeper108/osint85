# Contributing to osint85

Thank you for your interest in contributing to osint85! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)

## Code of Conduct

### Professional and Ethical Standards

- **Authorized Use Only**: All contributions must align with the ethical and legal use cases outlined in the README
- **No Malicious Features**: Do not contribute features designed for unauthorized access or exploitation
- **Responsible Disclosure**: If you discover security issues, report them privately
- **Respectful Collaboration**: Treat all contributors with respect and professionalism

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/osint85.git
   cd osint85
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/hellasleeper108/osint85.git
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv
- Git

### Setup Development Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-mock black flake8 mypy

# Install in editable mode
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your test API keys
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=osint85 --cov-report=html

# Run specific test file
pytest tests/unit/test_database.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black osint85/

# Lint code
flake8 osint85/

# Type checking
mypy osint85/
```

## How to Contribute

### Types of Contributions

We welcome:
- **Bug fixes**
- **Feature enhancements**
- **Documentation improvements**
- **Test coverage improvements**
- **Performance optimizations**
- **New search API providers**
- **Enhanced tagging patterns**

### Contribution Workflow

1. **Check existing issues** - Look for related issues or create a new one
2. **Discuss major changes** - For significant features, discuss in an issue first
3. **Create a branch** - Use descriptive branch names
4. **Make changes** - Follow coding standards
5. **Write tests** - Ensure adequate test coverage
6. **Update documentation** - Keep docs in sync with changes
7. **Submit PR** - Follow the PR template

## Coding Standards

### Python Style

- **PEP 8** compliance (enforced by flake8)
- **Type hints** for all function signatures
- **Docstrings** for all public functions and classes (Google style)
- **4 spaces** for indentation
- **100 characters** max line length

### Code Organization

```python
"""Module docstring explaining purpose."""

import standard_library
import third_party

from .local_module import something


# Constants
CONSTANT_NAME = "value"


class ClassName:
    """Class docstring."""

    def __init__(self, param: str):
        """Initialize class.

        Args:
            param: Parameter description
        """
        self.param = param

    def public_method(self) -> str:
        """Public method docstring.

        Returns:
            Description of return value
        """
        return self._private_method()

    def _private_method(self) -> str:
        """Private method docstring."""
        return self.param


def function_name(arg: str) -> bool:
    """Function docstring.

    Args:
        arg: Argument description

    Returns:
        Return value description

    Raises:
        ValueError: When and why this is raised
    """
    if not arg:
        raise ValueError("arg cannot be empty")
    return True
```

### Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `lowercase_with_underscores()`
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Private**: `_leading_underscore`

### Comments

- Use inline comments sparingly
- Explain **why**, not **what**
- Keep comments up to date with code changes
- Use docstrings for all public APIs

## Testing Guidelines

### Test Structure

```python
"""Test module for feature_name."""

import pytest
from osint85.module import ClassName


class TestClassName:
    """Tests for ClassName."""

    def test_method_success(self):
        """Test that method succeeds with valid input."""
        # Arrange
        instance = ClassName("test")

        # Act
        result = instance.method()

        # Assert
        assert result == expected_value

    def test_method_failure(self):
        """Test that method raises error with invalid input."""
        with pytest.raises(ValueError):
            instance = ClassName("")
            instance.method()

    def test_method_with_mock(self, mocker):
        """Test method with mocked dependencies."""
        mock_dependency = mocker.patch('osint85.module.dependency')
        mock_dependency.return_value = "mocked"

        result = ClassName("test").method()

        assert result == "expected"
        mock_dependency.assert_called_once()
```

### Test Coverage

- Aim for **80%+ coverage** for new code
- Test **happy paths** and **error cases**
- Test **edge cases** and **boundary conditions**
- Use **mocks** for external dependencies (LLM, search APIs)

### Test Naming

- `test_<method>_<condition>_<expected>`
- Examples:
  - `test_create_target_valid_input_returns_target`
  - `test_generate_dorks_no_api_key_raises_error`
  - `test_scan_with_mock_client_saves_results`

## Pull Request Process

### Before Submitting

- [ ] All tests pass
- [ ] Code is formatted with Black
- [ ] No linting errors (flake8)
- [ ] Type checking passes (mypy)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Commit messages follow conventions

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No new warnings
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance

**Examples:**
```
feat(dorks): add support for custom query templates

Allows users to define custom query templates for
specific reconnaissance patterns.

Closes #123

fix(scanner): handle timeout errors gracefully

Previously timeout errors would crash. Now they are
caught and logged with retry logic.

docs(readme): update installation instructions

Add troubleshooting section for common setup issues.
```

### Review Process

1. **Automated checks** must pass (tests, linting)
2. **Code review** by maintainer(s)
3. **Discussion** and requested changes
4. **Approval** and merge

## Areas for Contribution

### High Priority

- **Test coverage** - Expand unit and integration tests
- **Documentation** - Improve examples and guides
- **Error handling** - More robust error handling and logging
- **Performance** - Optimize database queries and LLM calls

### Medium Priority

- **Search providers** - Support for additional search APIs
- **Export formats** - JSON, CSV, HTML report export
- **Filtering** - Advanced result filtering options
- **TUI** - Terminal user interface with Textual

### Low Priority

- **Plugins** - Plugin system for extensions
- **CI/CD** - GitHub Actions workflows
- **Docker** - Containerization support
- **Web UI** - Optional web interface

### Good First Issues

Look for issues labeled `good-first-issue` for beginner-friendly contributions.

## Security

### Reporting Security Issues

**Do not** open public issues for security vulnerabilities.

Instead:
1. Email maintainers privately
2. Provide detailed description
3. Include steps to reproduce
4. Allow time for fix before disclosure

### Security Guidelines

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Validate all user inputs
- Follow secure coding practices
- Keep dependencies updated

## Questions?

- **Issues**: [GitHub Issues](https://github.com/hellasleeper108/osint85/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hellasleeper108/osint85/discussions)
- **Documentation**: [CLAUDE.md](CLAUDE.md)

---

Thank you for contributing to osint85! 🎉
