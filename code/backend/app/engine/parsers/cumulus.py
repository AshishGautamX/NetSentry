import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class CumulusParser(BaseParser):
    """
    Parser for Cumulus Linux network operating system configurations.
    Handles Debian-style interfaces, FRRouting (frr.conf), and Linux system networking syntax.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []
        current_context = "GLOBAL"

        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            is_blank = len(stripped) == 0
            is_comment = stripped.startswith("#") or stripped.startswith("!")

            if not is_blank and not is_comment:
                # Hierarchical blocks in FRR and interfaces
                if stripped.startswith("iface "):
                    parts = stripped.split()
                    current_context = f"interface {parts[1]}" if len(parts) > 1 else "interface"
                elif stripped.startswith("router "):
                    current_context = stripped
                elif stripped.startswith("line vty"):
                    current_context = "line vty"
                elif stripped.startswith("address-family "):
                    current_context = f"{current_context} > {stripped}"
                elif not raw_line.startswith(" ") and not raw_line.startswith("\t"):
                    # Top-level directive or block exit
                    if not any(stripped.startswith(k) for k in ["auto ", "allow-"]):
                        current_context = "GLOBAL"

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw_line,
                cleaned_text=stripped,
                section_context=current_context,
                is_comment=is_comment,
                is_blank=is_blank
            ))

        return parsed_lines
