import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class JuniperParser(BaseParser):
    """
    Parser for Juniper Junos configurations supporting both hierarchical bracket
    syntax and flat 'set' commands, maintaining block context.
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

            # Comments
            if stripped.startswith("/*") or stripped.startswith("#") or stripped.startswith("##"):
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack),
                    is_comment=True
                ))
                continue

            # Handle closing brace
            if stripped.startswith("}"):
                if context_stack:
                    context_stack.pop()
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                continue

            # Handle opening brace block
            if stripped.endswith("{"):
                block_name = stripped[:-1].strip()
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=" > ".join(context_stack)
                ))
                context_stack.append(block_name)
                continue

            # Regular statement (ends with semicolon or standalone)
            clean_cmd = stripped.rstrip(";").strip()
            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=clean_cmd,
                section_context=" > ".join(context_stack)
            ))

        return parsed_lines
