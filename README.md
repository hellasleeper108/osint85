# osint85

> Terminal-based OSINT assistant with LLM-powered dork generation

## ⚠️ LEGAL AND ETHICAL USAGE DISCLAIMER

**READ THIS BEFORE USING THIS TOOL**

osint85 is designed for **authorized security reconnaissance ONLY**. You are solely responsible for ensuring your use complies with all applicable laws and regulations.

### ✅ Permitted Use Cases

- Assets you **own** or **control**
- Systems with **explicit written permission** from the owner
- Authorized **bug bounty programs** (within scope)
- Controlled **lab/training environments**
- Internal **security audits** (authorized by your organization)

### ❌ Prohibited Uses

- Unauthorized reconnaissance or scanning
- Testing systems without permission
- Violating terms of service of search engines or APIs
- Any malicious, illegal, or unethical activities

### 📜 Legal Responsibility

**You are solely responsible** for:
- Obtaining proper authorization before use
- Ensuring compliance with all applicable laws
- Respecting terms of service and rate limits
- Using findings for defensive purposes only
- Reporting vulnerabilities responsibly

The authors and contributors of osint85 assume **no liability** for misuse or unauthorized use of this tool.

---

## What is osint85?

osint85 is a terminal-based OSINT (Open Source Intelligence) assistant that combines:

- 🤖 **LLM-powered query generation** - Natural language to advanced search operators
- 🔍 **Search API integration** - Automated result collection (no SERP scraping)
- 🏷️ **Smart tagging** - Automatic categorization of findings
- 📊 **AI summarization** - LLM-generated security reports
- 💾 **Project management** - SQLite-backed workflow
- 🖥️ **Clean CLI** - Terminal-first interface with optional TUI

Think of it as: `tmux brain` + `recon-ng` + `LLM` = osint85

---

## Features

### 🎯 Core Capabilities

- **Natural Language Target Profiling** - Describe your target in plain English
- **Automated Dork Generation** - LLM creates advanced search operator queries
- **Multi-Category Scanning** - Exposed backups, configs, staging, login portals, etc.
- **Result Tagging** - Automatic pattern-based tagging and scoring
- **Report Generation** - AI-powered markdown reports with findings and mitigations
- **Project Workflow** - Organize scans by target with SQLite storage

### 🔧 Technical Features

- Multiple LLM providers (Anthropic Claude, OpenAI GPT)
- Search API abstraction (SerpAPI, with extensible architecture)
- Rate limiting and retry logic
- Result deduplication
- Mock mode for testing without API calls

---

## Installation

### Prerequisites

- Python 3.10 or higher
- API keys for:
  - LLM provider (Anthropic or OpenAI)
  - Search API (SerpAPI or similar)

### Setup

```bash
# Clone the repository
git clone https://github.com/hellasleeper108/osint85.git
cd osint85

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install osint85 in editable mode
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` file with your API credentials:

```bash
# LLM Provider (choose one or both)
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
DEFAULT_LLM_PROVIDER=anthropic  # or openai

# Search API
SEARCH_API_KEY=your_serpapi_key_here
SEARCH_API_PROVIDER=serpapi

# Optional settings
LOG_LEVEL=INFO
MAX_RETRIES=3
REQUEST_TIMEOUT=30
```

---

## Quick Start

### 1. Create a Project

```bash
osint85 init \
  --name "Acme Corp Assessment" \
  --domain acme.com \
  --scope "Bug bounty program - public assets only"
```

### 2. Generate Dork Queries

```bash
osint85 dorks-generate \
  --goal "Find exposed backups, staging endpoints, and configuration files"
```

### 3. Review and Manage Queries

```bash
# List all generated queries
osint85 dorks-list

# Disable specific queries if needed
osint85 dorks-toggle 7,9,10 --disable
```

### 4. Run Scan

```bash
osint85 scan --max-results 30 --delay 2.0
```

### 5. Review Results

```bash
# List all results
osint85 results-list

# Filter by category
osint85 results-list --category exposed_backups

# Generate report
osint85 report --out reports/acme_initial.md
```

---

## Usage

### Commands

#### Project Management

```bash
# Create new project
osint85 init --name "Project Name" --domain example.com

# List all projects
osint85 projects
```

#### Dork Query Management

```bash
# Generate queries with AI
osint85 dorks-generate --goal "Your reconnaissance goal"

# List queries
osint85 dorks-list

# Enable/disable queries
osint85 dorks-toggle <query-ids> --enable
osint85 dorks-toggle <query-ids> --disable
```

#### Scanning

```bash
# Run scan with default settings
osint85 scan

# Custom scan parameters
osint85 scan --max-results 50 --delay 2.0

# Mock scan for testing (no API calls)
osint85 scan --mock
```

#### Results & Reporting

```bash
# List results
osint85 results-list

# Filter results
osint85 results-list --category exposed_backups --limit 100

# Generate full report
osint85 report --out reports/findings.md

# Quick summary
osint85 report --summary
```

#### Utility Commands

```bash
# Display legal disclaimer
osint85 disclaimer

# Show version
osint85 version

# Help
osint85 --help
osint85 <command> --help
```

---

## Example Workflow

```bash
# 1. Create project for bug bounty target
osint85 init --name "Example Corp" --domain example.com \
  --scope "Bug bounty program - authorized by example.com/security"

# 2. Generate comprehensive queries
osint85 dorks-generate --goal "Comprehensive reconnaissance covering:
  - Exposed directories and backups
  - Configuration files
  - Staging/dev environments
  - Login portals
  - API endpoints"

# 3. Review generated queries
osint85 dorks-list

# 4. Run scan (respectful rate limiting)
osint85 scan --max-results 30 --delay 2.0

# 5. Check results summary
osint85 report --summary

# 6. Generate detailed report
osint85 report --out reports/example-corp-$(date +%Y%m%d).md

# 7. Review specific category
osint85 results-list --category exposed_backups
```

---

## Architecture

### Component Overview

```
┌─────────────┐
│ CLI (Typer) │
└──────┬──────┘
       │
       ├─── ProjectManager ──► SQLite Database
       │                        ├─ targets
       │                        ├─ queries
       │                        └─ results
       │
       ├─── DorkGenerator ───► LLM Client ───► Anthropic/OpenAI
       │
       ├─── Scanner ─────────► Search Client ──► SerpAPI
       │                        │
       │                        └─► ResultProcessor (tagging)
       │
       └─── Reporter ────────► LLM Client ───► Markdown Reports
```

### Key Modules

- **`database.py`** - SQLite schema and ORM
- **`project.py`** - Project/target management
- **`llm_client.py`** - Unified LLM interface
- **`dorks.py`** - AI-powered query generation
- **`scanner.py`** - Search API abstraction
- **`reporting.py`** - AI-powered report generation
- **`__main__.py`** - CLI interface

---

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=osint85 tests/

# Lint code
flake8 osint85/

# Format code
black osint85/

# Type checking
mypy osint85/
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_database.py

# With coverage
pytest --cov=osint85 --cov-report=html
```

### Project Structure

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development guidelines.

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - | If using Anthropic |
| `OPENAI_API_KEY` | OpenAI API key | - | If using OpenAI |
| `DEFAULT_LLM_PROVIDER` | LLM provider | `anthropic` | No |
| `SEARCH_API_KEY` | Search API key | - | Yes |
| `SEARCH_API_PROVIDER` | Search provider | `serpapi` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `MAX_RETRIES` | Max API retries | `3` | No |
| `REQUEST_TIMEOUT` | Request timeout (s) | `30` | No |

### Database

By default, project data is stored in `.osint85/project.db` (gitignored).

### Reports

Generated reports are saved to `reports/` directory by default.

---

## Safety & Best Practices

### Authorization

1. **Always obtain written authorization** before scanning
2. **Document your scope** in the project configuration
3. **Stay within authorized boundaries**
4. **Respect rate limits** and ToS

### Rate Limiting

```bash
# Use appropriate delays between queries
osint85 scan --delay 2.0  # 2 seconds between queries

# Limit results to avoid excessive API usage
osint85 scan --max-results 20
```

### Responsible Disclosure

If you find security issues:

1. **Do not exploit** - reconnaissance only
2. **Document findings** using the report feature
3. **Report responsibly** following disclosure guidelines
4. **Do not publish** findings without permission

---

## Roadmap

### Phase 1 - MVP ✅
- [x] Core project structure
- [x] SQLite database
- [x] CLI interface
- [x] LLM integration
- [x] Dork generation
- [x] Search API client
- [x] Basic reporting

### Phase 2 - Enhancement
- [ ] Advanced result scoring
- [ ] Export to JSON/CSV
- [ ] Multiple search providers
- [ ] Enhanced filtering
- [ ] Improved error handling
- [ ] Comprehensive test suite

### Phase 3 - Polish
- [ ] TUI with Rich/Textual
- [ ] Interactive result browser
- [ ] Result deduplication improvements
- [ ] Performance optimization
- [ ] Plugin system
- [ ] CI/CD pipeline

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- Additional search API providers
- Enhanced tagging patterns
- Performance improvements
- Documentation
- Test coverage
- Bug fixes

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Search operators inspired by the OSINT community
- Built with [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), and [Anthropic Claude](https://www.anthropic.com/)

---

## Disclaimer (Again, Because It's Important)

🚨 **This tool is for authorized use only. You are responsible for ensuring your use complies with all laws and regulations. The authors assume no liability for misuse.** 🚨

By using osint85, you agree to:
- Use it only on authorized targets
- Comply with all applicable laws
- Respect terms of service
- Use findings for defensive purposes only
- Report vulnerabilities responsibly

**When in doubt, get explicit written permission first.**

---

## Support

- **Issues**: [GitHub Issues](https://github.com/hellasleeper108/osint85/issues)
- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Security**: Report security issues privately to the maintainers

---

**Happy (authorized and responsible) hunting!** 🔍✨
