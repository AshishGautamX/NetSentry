import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class CiscoParser(BaseParser):
    """
    Parser for Cisco IOS / IOS-XE / NX-OS configurations.
    Tracks line numbers, comments, hierarchical sections (line vty, interfaces, router, etc.).
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []
        current_section = ""
        in_banner = False
        banner_delimiter = None

        for idx, line_text in enumerate(lines, start=1):
            raw = line_text
            stripped = line_text.strip()

            # Handle blank lines
            if not stripped:
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text="",
                    section_context=current_section,
                    is_blank=True
                ))
                continue

            # Handle banner block delimiters
            if in_banner:
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=f"banner ({current_section})",
                    is_security_relevant=True
                ))
                if banner_delimiter and banner_delimiter in stripped:
                    in_banner = False
                    banner_delimiter = None
                continue

            # Handle comments
            if stripped.startswith("!"):
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=current_section,
                    is_comment=True
                ))
                continue

            # Check banner start
            banner_match = re.match(r'banner\s+(?:login|motd|exec)\s+(\S)', stripped, re.IGNORECASE)
            if banner_match:
                in_banner = True
                banner_delimiter = banner_match.group(1)
                parsed_lines.append(ParsedLine(
                    line_number=idx,
                    raw_text=raw,
                    cleaned_text=stripped,
                    section_context=current_section,
                    is_security_relevant=True
                ))
                continue

            # Check section header (unindented line that starts a block)
            if not raw.startswith(" ") and not raw.startswith("\t"):
                if re.match(r'^(line\s+\S+|interface\s+\S+|router\s+\S+|aaa\s+|snmp-server\s+group)', stripped, re.IGNORECASE):
                    current_section = stripped
                elif stripped.lower() in ("end", "exit"):
                    current_section = ""
                else:
                    # Top-level standalone command
                    current_section = ""

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw,
                cleaned_text=stripped,
                section_context=current_section
            ))

        return parsed_lines
