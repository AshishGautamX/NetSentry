from backend.app.engine.parsers.base import BaseParser, ParsedLine
from backend.app.engine.parsers.cisco import CiscoParser
from backend.app.engine.parsers.juniper import JuniperParser
from backend.app.engine.parsers.fortinet import FortinetParser
from backend.app.engine.parsers.paloalto import PaloAltoParser
from backend.app.engine.parsers.arista import AristaParser
from backend.app.engine.parsers.sonic import SonicParser
from backend.app.engine.parsers.cumulus import CumulusParser
from backend.app.engine.parsers.checkpoint import CheckpointParser
from backend.app.engine.parsers.sophos import SophosParser
from backend.app.engine.parsers.generic import GenericParser

def get_parser_for_vendor(vendor: str) -> BaseParser:
    v = vendor.lower() if vendor else ""
    if "cisco" in v:
        return CiscoParser()
    elif "juniper" in v:
        return JuniperParser()
    elif "fortinet" in v:
        return FortinetParser()
    elif "paloalto" in v or "palo" in v:
        return PaloAltoParser()
    elif "arista" in v:
        return AristaParser()
    elif "sonic" in v:
        return SonicParser()
    elif "cumulus" in v:
        return CumulusParser()
    elif "checkpoint" in v or "gaia" in v:
        return CheckpointParser()
    elif "sophos" in v or "sfos" in v:
        return SophosParser()
    else:
        return GenericParser()

__all__ = [
    "BaseParser",
    "ParsedLine",
    "CiscoParser",
    "JuniperParser",
    "FortinetParser",
    "PaloAltoParser",
    "AristaParser",
    "SonicParser",
    "CumulusParser",
    "CheckpointParser",
    "SophosParser",
    "GenericParser",
    "get_parser_for_vendor"
]
