import time
import pytest
from backend.app.engine.parsers.cisco import CiscoParser
from backend.app.engine.normalizer import NormalizationEngine

def test_ultra_large_config_parsing_and_normalization():
    """
    Performance benchmark: parses and normalizes a carrier-grade configuration
    exceeding 20,000 lines, ensuring sub-second to low-latency processing.
    """
    # 1. Build a synthetic 25,000-line enterprise configuration
    lines = [
        "hostname CARRIER-CORE-ROUTER-01",
        "ip domain name enterprise.net",
        "ip ssh version 2",
        "security passwords min-length 14",
        "no ip http server",
        "ip http secure-server",
        "ntp server 10.0.0.1",
        "logging host 10.0.0.2",
        "aaa new-model",
    ]

    # Add 4,000 interfaces (each 5 lines = 20,000 lines)
    for i in range(1, 4001):
        lines.append(f"interface GigabitEthernet0/0/{i}")
        lines.append(f" description Uplink to Node {i}")
        lines.append(f" ip address 10.{i // 256}.{i % 256}.1 255.255.255.0")
        lines.append(" no shutdown")
        lines.append("!")

    # Add line vty block
    lines.append("line vty 0 15")
    lines.append(" transport input ssh")
    lines.append(" exec-timeout 10 0")
    lines.append("!")

    config_text = "\n".join(lines)
    total_line_count = len(lines)
    assert total_line_count > 20000, f"Expected >20,000 lines, got {total_line_count}"

    # 2. Benchmark Parser
    t0 = time.perf_counter()
    parser = CiscoParser()
    parsed_lines = parser.parse(config_text)
    t1 = time.perf_counter()
    parse_time = t1 - t0

    assert len(parsed_lines) == total_line_count
    # Parser should easily process 20,000+ lines in under 1.5s
    assert parse_time < 2.0, f"Parsing took too long: {parse_time:.3f}s"

    # 3. Benchmark Normalization Engine
    t2 = time.perf_counter()
    normalizer = NormalizationEngine()
    processed_lines, baseline, unknown = normalizer.normalize(parsed_lines, vendor="cisco")
    t3 = time.perf_counter()
    normalize_time = t3 - t2

    # Normalization of 20,000+ lines with pre-compiled indexed regex should be under 1.5s
    assert normalize_time < 2.0, f"Normalization took too long: {normalize_time:.3f}s"

    # Verify accuracy of extracted baseline
    params = baseline["parameters"]
    assert params.get("security.ssh.version") == 2
    assert params.get("security.telnet.enabled") is False
    assert params.get("security.http_server.enabled") is False
    assert params.get("security.session_timeout") == 600

    print(f"\n[BENCHMARK RESULT] {total_line_count} lines parsed in {parse_time:.3f}s, normalized in {normalize_time:.3f}s. Total: {parse_time + normalize_time:.3f}s")
