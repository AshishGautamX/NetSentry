import pytest
from dataclasses import dataclass
from typing import Optional
from backend.app.engine.parsers.generic import GenericParser
from backend.app.engine.normalizer import NormalizationEngine

@dataclass
class MockLearnedMapping:
    vendor: str
    command_pattern: str
    normalized_param: str
    value_type: str = "int"
    extraction_regex: Optional[str] = None
    confidence: float = 1.0

def test_unknown_detection_and_relearning_flow():
    unfamiliar_config = """
    # Unfamiliar Device
    set security abc-session-timeout 300
    ip ssh version 2
    """
    parser = GenericParser()
    parsed_lines = parser.parse(unfamiliar_config)

    # First pass: No learned mapping
    normalizer = NormalizationEngine()
    lines_1, baseline_1, unknowns_1 = normalizer.normalize(parsed_lines, "custom_vendor", learned_mappings=[])

    # Assert that 'set security abc-session-timeout 300' was caught as unknown command
    assert len(unknowns_1) >= 1
    assert any("abc-session-timeout" in u["raw_command"] for u in unknowns_1)
    assert "security.session_timeout" not in baseline_1["parameters"]

    # Simulate administrator training the command in the Training Center
    trained_mapping = MockLearnedMapping(
        vendor="custom_vendor",
        command_pattern=r"set security abc-session-timeout\s+(?P<seconds>\d+)",
        normalized_param="security.session_timeout",
        value_type="int",
        confidence=1.0
    )

    # Second pass: With learned mapping present
    parsed_lines_2 = parser.parse(unfamiliar_config)
    lines_2, baseline_2, unknowns_2 = normalizer.normalize(
        parsed_lines_2, "custom_vendor", learned_mappings=[trained_mapping]
    )

    # Assert that the command is now automatically recognized
    assert "security.session_timeout" in baseline_2["parameters"]
    assert baseline_2["parameters"]["security.session_timeout"] == 300
    assert baseline_2["evidence"]["security.session_timeout"]["mapping_source"] == "LEARNED_KNOWLEDGE_BASE"
    assert baseline_2["evidence"]["security.session_timeout"]["confidence"] == 1.0
