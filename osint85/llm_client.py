"""LLM client abstraction for osint85."""

import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from .config import config


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Generate a response from the LLM.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User message
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to config)
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Generate a response using Claude.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User message
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to config)
        """
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

        self.api_key = api_key or config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        self.client = openai.OpenAI(api_key=self.api_key)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Generate a response using GPT.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User message
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Get an LLM client instance.

    Args:
        provider: LLM provider name (anthropic or openai), defaults to config

    Returns:
        LLMClient instance

    Raises:
        ValueError: If provider is invalid or not configured
    """
    provider = provider or config.DEFAULT_LLM_PROVIDER

    if provider == "anthropic":
        return AnthropicClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON response from LLM, extracting JSON if wrapped in markdown.

    Args:
        response: LLM response text

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If response is not valid JSON
    """
    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}") from e
