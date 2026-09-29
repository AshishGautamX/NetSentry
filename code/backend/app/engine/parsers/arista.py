from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class AristaParser(BaseParser):
    """
    Parser for Arista EOS configurations.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []
        current_section = ""

        for idx, line_text in enumerate(lines, start=1):
            raw = line_text
            stripped = line_text.strip()

            if not stripped:
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text="",
                    section_context=current_section,
                    is_blank=True
                ))
                continue

            if stripped.startswith("!"):
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=current_section,
                    is_comment=True
                ))
                continue

            # Check section header
            if not raw.startswith(" ") and not raw.startswith("\t"):
                if stripped.lower() in ("end", "exit"):
                    current_section = ""
                elif any(stripped.startswith(prefix) for prefix in ["management", "interface", "router", "aaa", "banner"]):
                    current_section = stripped
                else:
                    current_section = ""

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=stripped,
                section_context=current_section
            ))

        return parsed_lines
