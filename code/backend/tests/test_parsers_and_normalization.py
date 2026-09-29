import pytest
from backend.app.engine.parsers import get_parser_for_vendor
from backend.app.engine.normalizer import NormalizationEngine

def test_cisco_parser_and_normalization():
    sample = """
    hostname CORE-SW-01
    ip ssh version 2
    no ip http server
    security passwords min-length 14
    line vty 0 4
     transport input ssh
     exec-timeout 5 0
    """
    parser = get_parser_for_vendor("cisco")
    parsed_lines = parser.parse(sample)
    
    normalizer = NormalizationEngine()
    lines, baseline, unknowns = normalizer.normalize(parsed_lines, "cisco")
    
    params = baseline["parameters"]
    assert params["security.ssh.version"] == 2
    assert params["security.http_server.enabled"] is False
    assert params["security.password_policy.min_length"] == 14
    assert params["security.session_timeout"] == 300  # 5 min * 60s
    assert params["security.telnet.enabled"] is False

def test_juniper_parser_and_normalization():
    sample = """
    system {
        login {
            password {
                minimum-length 14;
            }
        }
        services {
            ssh {
                protocol-version v2;
            }
        }
    }
    """
    parser = get_parser_for_vendor("juniper")
    parsed_lines = parser.parse(sample)
    
    normalizer = NormalizationEngine()
    lines, baseline, unknowns = normalizer.normalize(parsed_lines, "juniper")
    
    params = baseline["parameters"]
    assert params["security.ssh.version"] == 2
    assert params["security.password_policy.min_length"] == 14

def test_fortinet_normalization():
    sample = """
    config system global
        set admin-ssh-v1 disable
        set admintimeout 10
    end
    """
    parser = get_parser_for_vendor("fortinet")
    parsed_lines = parser.parse(sample)
    
    normalizer = NormalizationEngine()
    lines, baseline, unknowns = normalizer.normalize(parsed_lines, "fortinet")
    
    params = baseline["parameters"]
    assert params["security.ssh.version"] == 2
    assert params["security.session_timeout"] == 600

def test_paloalto_normalization():
    sample = """
    set deviceconfig system service ssh-version-2 yes
    set deviceconfig system service disable-telnet yes
    set deviceconfig setting management idle-timeout 10
    """
    parser = get_parser_for_vendor("paloalto")
    parsed_lines = parser.parse(sample)
    
    normalizer = NormalizationEngine()
    lines, baseline, unknowns = normalizer.normalize(parsed_lines, "paloalto")
    
    params = baseline["parameters"]
    assert params["security.ssh.version"] == 2
    assert params["security.telnet.enabled"] is False
    assert params["security.session_timeout"] == 600
