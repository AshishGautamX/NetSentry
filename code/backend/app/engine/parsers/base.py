from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ParsedLine:
    line_number: int
    raw_text: str
    cleaned_text: str
    section_context: str
    is_comment: bool = False
    is_blank: bool = False
    is_security_relevant: bool = False
    normalized_param: Optional[str] = None
    extracted_value: Optional[Any] = None
    confidence: float = 0.0
    mapping_source: Optional[str] = None

class BaseParser:
    """
    Base parser providing line tracking, block hierarchy, and clean text extraction.
    """
    def parse(self, content: str) -> List[ParsedLine]:
        raise NotImplementedError
