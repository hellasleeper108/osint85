# CLAUDE.md - AI Assistant Guide for osint85

## Repository Overview

**Repository:** osint85
**Purpose:** [To be defined - appears to be related to OSINT (Open Source Intelligence) tools/utilities]
**Status:** New repository - Initial setup phase

This document serves as a comprehensive guide for AI assistants working on this codebase.

---

## Table of Contents

1. [Codebase Structure](#codebase-structure)
2. [Development Workflows](#development-workflows)
3. [Code Conventions](#code-conventions)
4. [Testing Strategy](#testing-strategy)
5. [Documentation Standards](#documentation-standards)
6. [Git Workflow](#git-workflow)
7. [AI Assistant Guidelines](#ai-assistant-guidelines)
8. [Dependencies & Tooling](#dependencies--tooling)

---

## Codebase Structure

### Current State
This is a new repository. As the codebase develops, maintain the following structure:

```
osint85/
├── src/                    # Source code
│   ├── lib/               # Reusable library code
│   ├── utils/             # Utility functions
│   ├── services/          # Business logic services
│   └── index.ts/js        # Main entry point
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test data/fixtures
├── docs/                  # Additional documentation
├── scripts/              # Build and utility scripts
├── examples/             # Usage examples
├── .github/              # GitHub workflows and templates
├── package.json          # Dependencies (if Node.js)
├── requirements.txt      # Dependencies (if Python)
├── README.md             # Project overview
├── CHANGELOG.md          # Version history
├── CONTRIBUTING.md       # Contribution guidelines
└── CLAUDE.md            # This file
```

### Key Directories

- **src/**: All production source code
- **tests/**: Comprehensive test suite with clear organization
- **docs/**: Extended documentation, architecture diagrams, API references
- **scripts/**: Automation scripts for development tasks

---

## Development Workflows

### Initial Setup

When setting up the project for the first time:

```bash
# Clone the repository
git clone <repository-url>
cd osint85

# Install dependencies (adjust based on language/framework)
npm install          # Node.js
# or
pip install -r requirements.txt  # Python
# or
go mod download     # Go

# Run tests to verify setup
npm test            # Node.js
# or
pytest              # Python
# or
go test ./...       # Go
```

### Development Cycle

1. **Create a feature branch**: `git checkout -b feature/description`
2. **Write tests first** (TDD approach recommended)
3. **Implement feature**
4. **Run tests and linters**
5. **Update documentation**
6. **Commit with meaningful messages**
7. **Push and create PR**

### Build & Test Commands

```bash
# Run all tests
npm test / pytest / go test

# Run tests with coverage
npm run test:coverage / pytest --cov / go test -cover

# Lint code
npm run lint / flake8 / golangci-lint

# Format code
npm run format / black . / gofmt

# Build for production
npm run build / python setup.py build / go build
```

---

## Code Conventions

### General Principles

1. **Clarity over cleverness**: Write code that's easy to understand
2. **DRY (Don't Repeat Yourself)**: Extract common patterns
3. **SOLID principles**: Follow object-oriented design principles
4. **Separation of concerns**: Keep modules focused and cohesive
5. **Error handling**: Always handle errors explicitly

### Naming Conventions

- **Files**: Use kebab-case for filenames (`user-service.ts`, `data-parser.py`)
- **Variables/Functions**: Use camelCase (`getUserData`, `parseResponse`)
- **Classes**: Use PascalCase (`DataProcessor`, `UserManager`)
- **Constants**: Use UPPER_SNAKE_CASE (`API_KEY`, `MAX_RETRIES`)
- **Private members**: Prefix with underscore (`_privateMethod`, `_internalState`)

### Code Style

- **Indentation**: 2 spaces for JS/TS, 4 spaces for Python
- **Line length**: Maximum 100 characters
- **Comments**: Explain "why", not "what"
- **Functions**: Keep functions small and focused (< 50 lines ideally)
- **Imports**: Group by external, internal, then relative

### Example Code Structure

**TypeScript/JavaScript:**
```typescript
// External imports
import axios from 'axios';
import { parseJson } from 'external-lib';

// Internal imports
import { logger } from '@/utils/logger';
import { ApiError } from '@/lib/errors';

// Types
interface UserData {
  id: string;
  name: string;
  email: string;
}

// Constants
const MAX_RETRY_ATTEMPTS = 3;
const API_TIMEOUT = 5000;

/**
 * Fetches user data from the API
 * @param userId - The unique identifier for the user
 * @returns Promise resolving to user data
 * @throws ApiError if the request fails
 */
export async function fetchUserData(userId: string): Promise<UserData> {
  try {
    const response = await axios.get(`/api/users/${userId}`, {
      timeout: API_TIMEOUT
    });
    return response.data;
  } catch (error) {
    logger.error(`Failed to fetch user ${userId}:`, error);
    throw new ApiError('User fetch failed', { userId, originalError: error });
  }
}
```

**Python:**
```python
"""User data management module."""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

# External imports
import requests

# Internal imports
from utils.logger import get_logger
from lib.errors import ApiError

# Constants
MAX_RETRY_ATTEMPTS = 3
API_TIMEOUT = 5

logger = get_logger(__name__)


@dataclass
class UserData:
    """Represents user data from the API."""
    id: str
    name: str
    email: str


def fetch_user_data(user_id: str) -> UserData:
    """
    Fetch user data from the API.

    Args:
        user_id: The unique identifier for the user

    Returns:
        UserData object with user information

    Raises:
        ApiError: If the request fails
    """
    try:
        response = requests.get(
            f'/api/users/{user_id}',
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return UserData(**data)
    except requests.RequestException as e:
        logger.error(f'Failed to fetch user {user_id}: {e}')
        raise ApiError(f'User fetch failed: {user_id}') from e
```

---

## Testing Strategy

### Test Organization

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test interactions between components
- **End-to-End Tests**: Test complete user workflows
- **Coverage Goal**: Aim for 80%+ code coverage

### Testing Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
2. **One assertion per test**: Focus each test on a single behavior
3. **Descriptive names**: Test names should describe the scenario
4. **Mock external dependencies**: Use mocks/stubs for APIs, databases
5. **Test edge cases**: Cover error conditions, empty inputs, boundaries

### Example Test Structure

**Jest (JavaScript/TypeScript):**
```typescript
describe('fetchUserData', () => {
  it('should return user data when API call succeeds', async () => {
    // Arrange
    const userId = 'user-123';
    const mockUserData = { id: userId, name: 'John', email: 'john@example.com' };
    jest.spyOn(axios, 'get').mockResolvedValue({ data: mockUserData });

    // Act
    const result = await fetchUserData(userId);

    // Assert
    expect(result).toEqual(mockUserData);
  });

  it('should throw ApiError when API call fails', async () => {
    // Arrange
    const userId = 'user-123';
    jest.spyOn(axios, 'get').mockRejectedValue(new Error('Network error'));

    // Act & Assert
    await expect(fetchUserData(userId)).rejects.toThrow(ApiError);
  });
});
```

**pytest (Python):**
```python
def test_fetch_user_data_success(mocker):
    """Test that fetch_user_data returns data when API call succeeds."""
    # Arrange
    user_id = 'user-123'
    mock_response = {'id': user_id, 'name': 'John', 'email': 'john@example.com'}
    mocker.patch('requests.get', return_value=Mock(json=lambda: mock_response))

    # Act
    result = fetch_user_data(user_id)

    # Assert
    assert result.id == user_id
    assert result.name == 'John'


def test_fetch_user_data_failure(mocker):
    """Test that fetch_user_data raises ApiError when API call fails."""
    # Arrange
    user_id = 'user-123'
    mocker.patch('requests.get', side_effect=requests.RequestException('Network error'))

    # Act & Assert
    with pytest.raises(ApiError):
        fetch_user_data(user_id)
```

---

## Documentation Standards

### README.md Structure

Every repository should have a comprehensive README:

```markdown
# Project Name

Brief description of what the project does.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

Step-by-step installation instructions

## Usage

Basic usage examples with code snippets

## Configuration

Environment variables and configuration options

## API Reference

Link to detailed API documentation

## Contributing

Link to CONTRIBUTING.md

## License

License information
```

### Code Documentation

- **Public APIs**: Document all public functions, classes, and modules
- **Complex Logic**: Add inline comments for non-obvious code
- **Type Annotations**: Use TypeScript types or Python type hints
- **JSDoc/Docstrings**: Use standard documentation formats

### Changelog Management

Maintain CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

## [Unreleased]

### Added
- New feature X

### Changed
- Modified behavior Y

### Deprecated
- Feature Z will be removed

### Removed
- Removed deprecated feature A

### Fixed
- Bug fix B

### Security
- Security patch C
```

---

## Git Workflow

### Branch Strategy

- **main/master**: Production-ready code, protected branch
- **develop**: Integration branch for features
- **feature/***: New features (`feature/add-user-auth`)
- **bugfix/***: Bug fixes (`bugfix/fix-login-error`)
- **hotfix/***: Urgent production fixes (`hotfix/security-patch`)
- **claude/***: AI assistant working branches (auto-generated)

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
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): add OAuth2 authentication

Implement OAuth2 flow with Google and GitHub providers.
Add token refresh mechanism and session management.

Closes #123
```

```
fix(api): handle timeout errors gracefully

Previously, timeout errors would crash the application.
Now they are caught and logged with appropriate user feedback.
```

### Pull Request Guidelines

1. **Title**: Clear, descriptive title following commit conventions
2. **Description**: Explain what, why, and how
3. **Tests**: Include test results and coverage
4. **Screenshots**: Add for UI changes
5. **Breaking Changes**: Clearly mark and explain
6. **Checklist**: Ensure all items are completed

**PR Template:**
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
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing
```

---

## AI Assistant Guidelines

### When Working on This Codebase

1. **Understand First**: Read existing code and documentation before making changes
2. **Ask Questions**: If requirements are unclear, ask for clarification
3. **Follow Conventions**: Match the existing code style and patterns
4. **Test Everything**: Write tests for new code, update tests for changes
5. **Document Changes**: Update relevant documentation
6. **Security First**: Never introduce security vulnerabilities
7. **Performance Matters**: Consider performance implications
8. **Error Handling**: Handle all error cases explicitly

### Common Tasks

#### Adding a New Feature

1. Check if related code exists
2. Create/update tests first (TDD)
3. Implement the feature following existing patterns
4. Update documentation
5. Run full test suite
6. Commit with descriptive message

#### Fixing a Bug

1. Reproduce the bug
2. Write a failing test that captures the bug
3. Fix the bug
4. Verify the test passes
5. Check for similar bugs elsewhere
6. Update documentation if needed

#### Refactoring Code

1. Ensure comprehensive test coverage exists
2. Make incremental changes
3. Run tests after each change
4. Keep commits small and focused
5. Document architectural decisions

### Security Considerations

Always check for these vulnerabilities:

- **Injection attacks**: SQL, NoSQL, command injection
- **XSS**: Cross-site scripting
- **CSRF**: Cross-site request forgery
- **Authentication/Authorization**: Proper access controls
- **Sensitive Data**: Never commit secrets, keys, passwords
- **Dependencies**: Keep dependencies updated, check for vulnerabilities
- **Input Validation**: Validate and sanitize all user inputs
- **Error Messages**: Don't expose sensitive information in errors

### Code Review Checklist

Before considering code complete:

- [ ] Code follows project conventions
- [ ] All tests pass
- [ ] Test coverage is adequate
- [ ] No security vulnerabilities introduced
- [ ] Error handling is comprehensive
- [ ] Documentation is updated
- [ ] Performance is acceptable
- [ ] Code is readable and maintainable
- [ ] Edge cases are handled
- [ ] Breaking changes are documented

---

## Dependencies & Tooling

### Package Management

**Node.js (if applicable):**
- Use `package-lock.json` for deterministic builds
- Keep dependencies up to date
- Use `npm audit` to check for vulnerabilities
- Prefer well-maintained packages with active communities

**Python (if applicable):**
- Use virtual environments (`venv` or `conda`)
- Pin dependencies in `requirements.txt`
- Use `pip-audit` or `safety` for security checks
- Consider using `poetry` or `pipenv` for dependency management

**Go (if applicable):**
- Use Go modules (`go.mod`)
- Run `go mod tidy` to clean up dependencies
- Use `go mod verify` to check integrity

### Recommended Tools

#### Linting & Formatting
- **JavaScript/TypeScript**: ESLint, Prettier
- **Python**: flake8, black, mypy, pylint
- **Go**: golangci-lint, gofmt

#### Testing
- **JavaScript/TypeScript**: Jest, Vitest, Mocha
- **Python**: pytest, unittest
- **Go**: built-in testing, testify

#### CI/CD
- GitHub Actions
- Pre-commit hooks (husky for Node.js, pre-commit for Python)

#### Documentation
- JSDoc / TSDoc for JavaScript/TypeScript
- Sphinx for Python
- godoc for Go

### Environment Variables

Never commit sensitive data. Use environment variables:

```bash
# .env.example (commit this)
API_KEY=your_api_key_here
DATABASE_URL=postgresql://localhost/dbname
LOG_LEVEL=info

# .env (DO NOT commit this - add to .gitignore)
API_KEY=actual_secret_key
DATABASE_URL=postgresql://user:pass@prod-server/db
LOG_LEVEL=debug
```

---

## Project-Specific Guidelines

### OSINT Focus

Given the repository name "osint85", this project likely involves OSINT (Open Source Intelligence) tools. When working on this codebase:

1. **Privacy & Ethics**: Respect privacy laws and ethical boundaries
2. **Data Sources**: Document all data sources clearly
3. **Rate Limiting**: Implement rate limiting for API calls
4. **Caching**: Cache results to minimize redundant requests
5. **Attribution**: Properly attribute data sources
6. **Compliance**: Ensure compliance with ToS of data sources

### Best Practices for OSINT Tools

- **Modular Design**: Separate data collection, processing, and presentation
- **Configurable**: Allow users to configure data sources and parameters
- **Logging**: Comprehensive logging for audit trails
- **Error Resilience**: Handle API failures and rate limits gracefully
- **Data Validation**: Validate and sanitize all collected data
- **Export Formats**: Support multiple export formats (JSON, CSV, etc.)

---

## Updating This Document

This CLAUDE.md should be kept up to date as the project evolves:

- Update structure as directories are added/changed
- Document new workflows and conventions
- Add project-specific guidelines as they emerge
- Keep examples current with the actual codebase
- Add lessons learned from development

**Last Updated**: 2025-11-18
**Version**: 1.0.0 (Initial version for new repository)

---

## Quick Reference

### Essential Commands

```bash
# Setup
git clone <repo-url> && cd osint85
[npm install / pip install -r requirements.txt / go mod download]

# Development
git checkout -b feature/my-feature
[npm run dev / python main.py / go run .]

# Testing
[npm test / pytest / go test ./...]

# Commit
git add .
git commit -m "feat: add new feature"
git push -u origin feature/my-feature

# CI/CD
[npm run lint / flake8 / golangci-lint run]
[npm run build / python setup.py build / go build]
```

### Key Files to Review

- `README.md`: Project overview and getting started
- `CONTRIBUTING.md`: How to contribute
- `package.json` / `requirements.txt` / `go.mod`: Dependencies
- `.github/workflows/`: CI/CD configuration
- `tests/`: Test suite organization

---

## Getting Help

- **Issues**: Check existing GitHub issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Review the `/docs` directory
- **Code Comments**: Look for inline documentation in the code

---

## License

[To be determined - Add license information once established]
