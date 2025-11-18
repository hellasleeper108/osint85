# Changelog

All notable changes to osint85 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- TUI interface with Rich/Textual
- Multiple search API providers
- Enhanced result filtering and scoring
- Export to JSON/CSV formats
- Plugin system for extensibility

## [0.1.0] - 2025-11-18

### Added
- Initial release of osint85
- Core project structure and architecture
- SQLite database for project management
- CLI interface with Typer
- LLM integration (Anthropic Claude, OpenAI GPT)
- AI-powered dork query generation
- Search API client (SerpAPI)
- Mock search client for testing
- Result tagging and processing
- AI-powered report generation
- Project-based workflow
- Comprehensive documentation (README.md, CLAUDE.md)
- Legal and ethical usage disclaimers
- Configuration management via .env
- Rate limiting and retry logic

### Commands Implemented
- `osint85 init` - Create new projects
- `osint85 projects` - List all projects
- `osint85 dorks-generate` - Generate queries with LLM
- `osint85 dorks-list` - List queries
- `osint85 dorks-toggle` - Enable/disable queries
- `osint85 scan` - Run search queries
- `osint85 results-list` - List results
- `osint85 report` - Generate reports
- `osint85 disclaimer` - Show legal disclaimer
- `osint85 version` - Show version info

[Unreleased]: https://github.com/hellasleeper108/osint85/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hellasleeper108/osint85/releases/tag/v0.1.0
