from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class GenericParser(BaseParser):
    """
    Fallback generic parser for any network configuration syntax,
    preserving lines, line numbers, and comment detection.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []

        for idx, line_text in enumerate(lines, start=1):
            raw = line_text
            stripped = line_text.strip()

            if not stripped:
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text="",
                    section_context="",
                    is_blank=True
                ))
                continue

            is_comment = any(stripped.startswith(prefix) for prefix in ["!", "#", "//", ";", "/*"])

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=stripped,
                section_context="",
                is_comment=is_comment
            ))

        return parsed_lines
