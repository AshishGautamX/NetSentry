import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class CheckpointParser(BaseParser):
    """
    Parser for Check Point Gaia OS clish command line configuration exports.
    Tracks command hierarchy (e.g. set snmp, set ntp, set aaa, set user).
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []

        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            is_blank = len(stripped) == 0
            is_comment = stripped.startswith("#") or stripped.startswith(";")

            context = "GLOBAL"
            if not is_blank and not is_comment:
                parts = stripped.split()
                if len(parts) >= 2 and parts[0] in ["set", "add", "delete"]:
                    context = f"{parts[0]} {parts[1]}"

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw_line,
                cleaned_text=stripped,
                section_context=context,
                is_comment=is_comment,
                is_blank=is_blank
            ))

        return parsed_lines
