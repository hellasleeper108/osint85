# CLAUDE.md - AI Assistant Guide for osint85

## Repository Overview

**Repository:** osint85
**Purpose:** Terminal-based OSINT assistant with LLM-powered dork generation
**Language:** Python 3.10+
**Status:** Active development

## What is osint85?

osint85 is a terminal-based OSINT (Open Source Intelligence) assistant that combines the power of LLMs with advanced search operators for defensive security and authorized reconnaissance.

**Key Features:**
- Natural language target profiling
- LLM-powered generation of search operator queries ("dorks")
- Automated search API integration (no direct SERP scraping)
- Result aggregation, tagging, and filtering
- AI-powered summarization and reporting
- Project-based workflow with SQLite storage
- Clean terminal interface (optional TUI later)

**Use Cases:**
- Bug bounty reconnaissance (authorized targets only)
- Internal security audits
- Defensive security assessments
- Educational/lab environments

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

### Project Layout

```
osint85/
├── osint85/                 # Main Python package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # CLI entry point
│   ├── project.py          # Project & target management
│   ├── dorks.py            # LLM-powered dork generation
│   ├── scanner.py          # Search API client & result processing
│   ├── reporting.py        # LLM summarization & markdown reports
│   ├── database.py         # SQLite schema & migrations
│   ├── config.py           # Configuration management
│   └── llm_client.py       # LLM API integration (Anthropic, OpenAI, etc.)
├── tests/                   # Test suite
│   ├── unit/               # Unit tests for each module
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data & mock responses
├── docs/                    # Documentation
│   └── architecture.md     # Architecture diagrams & decisions
├── examples/                # Usage examples
│   └── sample_session.md   # Example CLI workflow
├── .osint85/               # Per-project data (gitignored)
│   └── project.db          # SQLite database for each project
├── requirements.txt         # Python dependencies
├── setup.py                # Package installation
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore patterns
├── README.md               # Project overview & getting started
├── CHANGELOG.md            # Version history
├── LICENSE                 # License (MIT recommended)
└── CLAUDE.md               # This file
```

### Key Directories & Files

- **osint85/**: Core Python package containing all application logic
  - `__main__.py`: CLI interface using Typer
  - `project.py`: Project/target management, SQLite interaction
  - `dorks.py`: LLM prompt engineering for query generation
  - `scanner.py`: Search API abstraction & result processing
  - `reporting.py`: Report generation with LLM summarization
  - `database.py`: Database schema, migrations, models
  - `llm_client.py`: Unified LLM client supporting multiple providers

- **tests/**: Comprehensive test coverage with mocked LLM/API responses
- **.osint85/**: Runtime project data (one DB per project, gitignored)
- **examples/**: Real-world usage examples and tutorials

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

### Architecture Overview

osint85 follows a modular pipeline architecture:

```
User Input → Profile → LLM → Dorks → Search API → Results → LLM → Report
```

**Component Responsibilities:**

1. **Project Manager** (`project.py`):
   - SQLite CRUD operations for targets, queries, results
   - Project lifecycle management
   - Scope validation

2. **Dork Generator** (`dorks.py`):
   - LLM prompt engineering for query generation
   - Structured JSON output parsing
   - Query categorization and risk scoring

3. **Scanner** (`scanner.py`):
   - Search API abstraction layer
   - Result deduplication and tagging
   - Rate limiting and retry logic

4. **Reporter** (`reporting.py`):
   - LLM-powered summarization
   - Markdown/HTML report generation
   - Findings categorization

5. **LLM Client** (`llm_client.py`):
   - Unified interface for multiple providers (Anthropic, OpenAI)
   - Prompt templating and response parsing
   - Error handling and retries

### OSINT-Specific Best Practices

**Legal & Ethical Requirements:**

1. **Authorized Use Only**: Use only on assets you own or have explicit permission to test
2. **Bug Bounty Compliance**: Respect scope definitions in bug bounty programs
3. **No Exploitation**: Discovery and reporting only - no active exploitation
4. **Privacy Laws**: Comply with GDPR, CCPA, and local privacy regulations
5. **Terms of Service**: Respect search API ToS and rate limits

**Technical Best Practices:**

- **Modular Design**: Clear separation between data collection, processing, and presentation
- **Configurable Scope**: Per-project scope definitions to prevent out-of-bounds searches
- **Rate Limiting**: Respect API limits; implement exponential backoff
- **Caching**: Cache search results to minimize redundant API calls
- **Audit Trails**: Log all queries and results for accountability
- **Data Sanitization**: Validate and sanitize all external data
- **Error Resilience**: Graceful handling of API failures and timeouts

**Safety Checklist:**

- [ ] Project scope clearly defined
- [ ] Authorization documented
- [ ] No automated exploitation features
- [ ] Rate limiting implemented
- [ ] Results stored securely
- [ ] Sensitive data handling procedures in place
- [ ] Disclaimer visible in README and CLI

### LLM Integration Patterns

**Dork Generation Prompt:**

```python
SYSTEM_PROMPT = """
You generate advanced search-operator queries for open-source recon and defensive security.
You only generate queries and short metadata in pure JSON.
Never include instructions, prose, or comments.
Respond strictly as:
{
  "queries": [
    {
      "category": "string",
      "risk_level": "low|medium|high",
      "description": "short human description",
      "query": "search operator query string here"
    }
  ]
}
"""

USER_PROMPT = {
  "target": {
    "name": "...",
    "primary_domain": "...",
    "scope": "...",
    "notes": "..."
  },
  "goal": "..."
}
```

**Report Generation Prompt:**

```python
SYSTEM_PROMPT = """
You are a defensive security analyst.
You receive URLs & snippets from advanced search queries.
Group by category, describe implications, suggest mitigations.
Respond in markdown, concise, no exploitation steps.
This is for internal audit/awareness, not attack.
"""
```

### Development Priorities

**Phase 1 - MVP:**
- [x] Project structure
- [ ] SQLite schema
- [ ] CLI with basic commands
- [ ] LLM client integration
- [ ] Basic dork generation
- [ ] Search API client (with mock for testing)
- [ ] Simple reporting

**Phase 2 - Enhancement:**
- [ ] Result tagging & scoring
- [ ] Advanced filtering
- [ ] Multiple LLM provider support
- [ ] Export to JSON/CSV
- [ ] Improved error handling

**Phase 3 - Polish:**
- [ ] TUI with Rich/Textual
- [ ] Interactive result browsing
- [ ] Result deduplication improvements
- [ ] Performance optimization
- [ ] Comprehensive testing

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
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .  # Install in editable mode

# Environment
cp .env.example .env
# Edit .env with your API keys

# Usage
osint85 init --name "My Project" --domain example.com
osint85 dorks generate --goal "Find exposed backups"
osint85 scan run --max-results 30
osint85 results list
osint85 report generate --out report.md

# Development
git checkout -b feature/my-feature
python -m pytest tests/  # Run tests
flake8 osint85/          # Lint
black osint85/           # Format

# Commit
git add .
git commit -m "feat: add new feature"
git push -u origin feature/my-feature
```

### Key Files to Review

- `README.md`: Project overview, getting started, safety disclaimers
- `requirements.txt`: Python dependencies
- `osint85/__main__.py`: CLI entry point and command definitions
- `osint85/database.py`: Database schema and models
- `.env.example`: Required environment variables
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
