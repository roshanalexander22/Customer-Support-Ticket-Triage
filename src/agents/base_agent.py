"""Base Agent class supporting LLM inference and deterministic heuristic fallbacks."""

import json
import logging
from typing import Dict, Any, Optional
from src.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class providing LLM connectivity and fallback intelligence."""

    def __init__(self, name: str, role_description: str):
        self.name = name
        self.role_description = role_description
        self.client = None
        self._init_llm_client()

    def _init_llm_client(self) -> None:
        """Initialize Google GenAI client if an API key is configured."""
        if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info(f"Agent {self.name}: Initialized Gemini client ({GEMINI_MODEL})")
            except Exception as e:
                logger.warning(f"Agent {self.name}: Failed to init Gemini client: {e}. Falling back to heuristic mode.")
                self.client = None
        else:
            self.client = None

    def query_llm(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        """Invoke Gemini LLM with error handling."""
        if not self.client:
            return None
        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"system_instruction": system_instruction, "temperature": 0.2}
            )
            return response.text if response else None
        except Exception as e:
            logger.warning(f"Agent {self.name} LLM call error: {e}. Utilizing fallback engine.")
            return None
