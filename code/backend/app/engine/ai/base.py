from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAIProvider(ABC):
    """
    Abstract AI Provider interface for semantic command interpretation.
    """
    @abstractmethod
    async def analyze_security_impact(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the defensible security impact of a failed compliance finding."""
        pass

    @abstractmethod
    async def interpret_command(self, vendor: str, command: str, context: str = "") -> Dict[str, Any]:
        """
        Interprets an unfamiliar network configuration command.
        Returns:
            {
                "suggested_parameter": str,
                "suggested_category": str,
                "confidence": float,
                "explanation": str
            }
        """
        pass
