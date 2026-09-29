import json
import re
from typing import List
from backend.app.engine.parsers.base import BaseParser, ParsedLine

class SonicParser(BaseParser):
    """
    Parser for SONiC (Software for Open Networking in the Cloud).
    Supports both JSON config_db.json schemas and SONiC CLI configuration exports.
    """

    def parse(self, content: str) -> List[ParsedLine]:
        lines = content.splitlines()
        parsed_lines: List[ParsedLine] = []

        # Check if content is valid JSON (standard SONiC config_db.json format)
        stripped = content.strip()
        is_json = False
        json_data = None
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                json_data = json.loads(content)
                is_json = True
            except Exception:
                is_json = False

        if is_json and isinstance(json_data, dict):
            return self._parse_sonic_json(lines, json_data)
        else:
            return self._parse_sonic_cli(lines)

    def _parse_sonic_json(self, lines: List[str], json_data: dict) -> List[ParsedLine]:
        parsed_lines: List[ParsedLine] = []
        current_table = "GLOBAL"
        current_sub = ""

        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            is_blank = len(stripped) == 0
            is_comment = stripped.startswith("#") or stripped.startswith("//")

            # Check indentation level to determine if top-level table or sub-block
            indent = len(raw_line) - len(raw_line.lstrip())

            # Top-level table (typically 2 spaces indentation in config_db.json)
            tbl_match = re.search(r'^\s{1,3}"([A-Z0-9_]+)":\s*\{', raw_line)
            if tbl_match:
                current_table = tbl_match.group(1)
                current_sub = ""
            elif indent >= 4:
                sub_match = re.search(r'^\s{4,6}"([^"]+)":\s*\{', raw_line)
                if sub_match:
                    current_sub = sub_match.group(1)

            context = f"{current_table} > {current_sub}" if current_sub else current_table

            # Construct clean semantic representation
            cleaned = stripped.rstrip(",").strip()
            # If line is `"key": "value"`, create a clean semantic command
            kv_match = re.search(r'"([^"]+)":\s*("?[^"]+"?)', stripped)
            if kv_match:
                k, v = kv_match.group(1), kv_match.group(2).strip('"')
                cleaned = f"{current_table} {k} {v}"

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw_line,
                cleaned_text=cleaned,
                section_context=context,
                is_comment=is_comment,
                is_blank=is_blank
            ))

        return parsed_lines

    def _parse_sonic_cli(self, lines: List[str]) -> List[ParsedLine]:
        parsed_lines: List[ParsedLine] = []
        context = "GLOBAL"

        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            is_blank = len(stripped) == 0
            is_comment = stripped.startswith("#") or stripped.startswith("//") or stripped.startswith(";")

            if not is_blank and not is_comment:
                if stripped.startswith("config "):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        context = f"config > {parts[1]}"
                elif not raw_line.startswith(" ") and not raw_line.startswith("\t"):
                    context = "GLOBAL"

            parsed_lines.append(ParsedLine(
                line_number=idx,
                raw_text=raw_line,
                cleaned_text=stripped,
                section_context=context,
                is_comment=is_comment,
                is_blank=is_blank
            ))

        return parsed_lines
