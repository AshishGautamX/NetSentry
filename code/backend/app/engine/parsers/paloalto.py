from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class PaloAltoParser(BaseParser):
    """
    Parser for Palo Alto PAN-OS configurations (set-syntax & hierarchy).
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

            if stripped.startswith("#") or stripped.startswith("<!--"):
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context="",
                    is_comment=True
                ))
                continue

            # Determine section context from set path
            section = ""
            if stripped.startswith("set "):
                tokens = stripped.split()
                if len(tokens) >= 3:
                    section = " ".join(tokens[1:3])

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=stripped,
                section_context=section
            ))

        return parsed_lines
