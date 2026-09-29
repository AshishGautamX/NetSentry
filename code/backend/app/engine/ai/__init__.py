from backend.app.engine.ai.base import BaseAIProvider
from backend.app.engine.ai.deterministic import DeterministicAIProvider
from backend.app.engine.ai.gemini_provider import GeminiAIProvider
from backend.app.services.settings_service import resolve_ai_provider, resolve_gemini_api_key

def get_ai_provider() -> BaseAIProvider:
    provider = resolve_ai_provider()
    if provider == "gemini":
        api_key = resolve_gemini_api_key()
        if api_key:
            return GeminiAIProvider(api_key=api_key)
    return DeterministicAIProvider()

__all__ = [
    "BaseAIProvider",
    "DeterministicAIProvider",
    "GeminiAIProvider",
    "get_ai_provider"
]
