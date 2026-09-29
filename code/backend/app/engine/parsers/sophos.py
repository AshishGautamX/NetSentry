import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class SophosParser(BaseParser):
    """
    Parser for Sophos Firewall (SFOS) CLI and configuration backups.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []

        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            # Strip prompt if present (e.g. console> )
            clean_cmd = re.sub(r'^(?:console|[A-Za-z0-9\-_]+)>\s*', '', stripped)
            is_blank = len(clean_cmd) == 0
            is_comment = clean_cmd.startswith("#") or clean_cmd.startswith("!")

            context = "GLOBAL"
            if not is_blank and not is_comment:
                parts = clean_cmd.split()
                if len(parts) >= 2:
                    context = f"{parts[0]} {parts[1]}"

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw_line,
                cleaned_text=clean_cmd,
                section_context=context,
                is_comment=is_comment,
                is_blank=is_blank
            ))

        return parsed_lines
