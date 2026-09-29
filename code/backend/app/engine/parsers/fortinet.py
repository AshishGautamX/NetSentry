from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class FortinetParser(BaseParser):
    """
    Parser for Fortinet FortiOS configuration files with config/edit/set/next/end hierarchies.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []
        context_stack: List[str] = []

        for idx, line_text in enumerate(lines, start=1):
            raw = line_text
            stripped = line_text.strip()

            if not stripped:
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text="",
                    section_context=" > ".join(context_stack),
                    is_blank=True
                ))
                continue

            if stripped.startswith("#"):
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack),
                    is_comment=True
                ))
                continue

            # Entering config block
            if stripped.startswith("config "):
                context_stack.append(stripped)
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                continue

            # Entering edit block
            if stripped.startswith("edit "):
                context_stack.append(stripped)
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                continue

            # Exiting edit block (next)
            if stripped == "next":
                if context_stack and context_stack[-1].startswith("edit "):
                    context_stack.pop()
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                continue

            # Exiting config block (end)
            if stripped == "end":
                if context_stack and context_stack[-1].startswith("config "):
                    context_stack.pop()
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                continue

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=stripped,
                section_context=" > ".join(context_stack)
            ))

        return parsed_lines
