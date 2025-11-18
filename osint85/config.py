"""Configuration management for osint85."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # LLM Configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "anthropic")

    # Search API Configuration
    SEARCH_API_KEY: Optional[str] = os.getenv("SEARCH_API_KEY")
    SEARCH_API_PROVIDER: str = os.getenv("SEARCH_API_PROVIDER", "serpapi")

    # Application Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", ".osint85/project.db")

    # Rate Limiting
    SEARCH_RATE_LIMIT: int = int(os.getenv("SEARCH_RATE_LIMIT", "10"))
    LLM_RATE_LIMIT: int = int(os.getenv("LLM_RATE_LIMIT", "50"))

    # Directories
    REPORTS_DIR: Path = Path("reports")
    OSINT_DIR: Path = Path(".osint85")

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []

        # Check for required API keys based on provider
        if cls.DEFAULT_LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic as LLM provider")
        elif cls.DEFAULT_LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI as LLM provider")

        if not cls.SEARCH_API_KEY:
            errors.append("SEARCH_API_KEY is required for search functionality")

        if errors:
            for error in errors:
                print(f"[ERROR] {error}")
            return False

        return True

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        cls.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.OSINT_DIR.mkdir(parents=True, exist_ok=True)


# Create singleton instance
config = Config()
