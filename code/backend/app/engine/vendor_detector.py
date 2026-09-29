import re
from typing import Dict, Any

class VendorDetector:
    """
    Identifies vendor, platform, OS version, and hostname from network configuration files
    using signature patterns and heuristics.
    """

    @classmethod
    def detect(cls, content: str) -> Dict[str, Any]:
        result = {
            "vendor": "unknown",
            "model": "Generic Network Device",
            "os_version": "Unknown OS",
            "hostname": "UNKNOWN-DEVICE",
            "confidence": 0.40
        }

        # Check Juniper
        if re.search(r'## Last changed:|set system services|system\s*\{|version\s+\d+\.\d+R', content, re.IGNORECASE):
            result["vendor"] = "juniper"
            result["model"] = "SRX Series / MX Series"
            result["confidence"] = 0.95
            
            # Junos version
            v_match = re.search(r'version\s+([0-9A-Za-z\.\-_]+);', content)
            if v_match:
                result["os_version"] = f"Junos {v_match.group(1)}"
            
            # Junos hostname
            h_match = re.search(r'host-name\s+([A-Za-z0-9\-_]+);', content)
            if not h_match:
                h_match = re.search(r'set system host-name\s+([A-Za-z0-9\-_]+)', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Fortinet FortiOS
        if re.search(r'#build-version:|#config-version:|config system global|set admintimeout', content, re.IGNORECASE):
            result["vendor"] = "fortinet"
            result["model"] = "FortiGate Security Gateway"
            result["confidence"] = 0.95
            
            v_match = re.search(r'#build-version:\s*([A-Za-z0-9\.\-_]+)', content)
            if v_match:
                result["os_version"] = f"FortiOS {v_match.group(1)}"
                if "FGT" in v_match.group(1):
                    result["model"] = v_match.group(1).split("-")[0]
            
            h_match = re.search(r'set\s+hostname\s+"?([A-Za-z0-9\-_]+)"?', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Palo Alto PAN-OS
        if re.search(r'set deviceconfig|set mgt-config|<config\s+version=|pan-os', content, re.IGNORECASE):
            result["vendor"] = "paloalto"
            result["model"] = "PA Next-Gen Firewall"
            result["os_version"] = "PAN-OS"
            result["confidence"] = 0.92
            
            h_match = re.search(r'set deviceconfig system hostname\s+([A-Za-z0-9\-_]+)', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Arista EOS
        if re.search(r'! Command: show running-config|transceiver qsfp|management api http-commands|management ssh', content, re.IGNORECASE):
            result["vendor"] = "arista"
            result["model"] = "EOS Switch / Router"
            result["confidence"] = 0.93
            
            v_match = re.search(r'EOS-([0-9A-Za-z\.\-_]+)', content)
            if v_match:
                result["os_version"] = f"EOS {v_match.group(1)}"
            
            dev_match = re.search(r'! device:\s*([A-Za-z0-9\-_]+)\s*\(([^,]+)', content)
            if dev_match:
                result["hostname"] = dev_match.group(1)
                result["model"] = dev_match.group(2).strip()
            else:
                h_match = re.search(r'^hostname\s+([A-Za-z0-9\-_]+)', content, re.MULTILINE)
                if h_match:
                    result["hostname"] = h_match.group(1)
            return result

        # Check SONiC (Software for Open Networking in the Cloud)
        if re.search(r'"DEVICE_METADATA"|sonic-cli|sonic_version|sonic-utilities|"MGMT_INTERFACE"', content, re.IGNORECASE):
            result["vendor"] = "sonic"
            result["model"] = "SONiC Open Whitebox Switch"
            result["os_version"] = "SONiC NOS"
            result["confidence"] = 0.94
            
            h_match = re.search(r'"hostname":\s*"([^"]+)"', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            p_match = re.search(r'"platform":\s*"([^"]+)"', content)
            if p_match:
                result["model"] = p_match.group(1)
            return result

        # Check Cumulus Linux
        if re.search(r'Cumulus Linux|cumulus@|/etc/network/interfaces|frr version', content, re.IGNORECASE):
            result["vendor"] = "cumulus"
            result["model"] = "Cumulus Open Networking Switch"
            result["os_version"] = "Cumulus Linux"
            result["confidence"] = 0.93
            
            h_match = re.search(r'hostname\s+([A-Za-z0-9\-_]+)', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Check Point Gaia OS
        if re.search(r'Check Point Gaia|set clish|add aaa radius|set snmp agent|gaia', content, re.IGNORECASE):
            result["vendor"] = "checkpoint"
            result["model"] = "Check Point Quantum Security Gateway"
            result["os_version"] = "Gaia OS"
            result["confidence"] = 0.92
            
            h_match = re.search(r'set hostname\s+([A-Za-z0-9\-_]+)', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Sophos Firewall (SFOS)
        if re.search(r'SFOS|Sophos Firewall|Sophos XG|system-diagnostics', content, re.IGNORECASE):
            result["vendor"] = "sophos"
            result["model"] = "Sophos XGS Next-Gen Firewall"
            result["os_version"] = "Sophos SFOS"
            result["confidence"] = 0.92
            
            h_match = re.search(r'(?:set system-hostname|hostname)\s+([A-Za-z0-9\-_]+)', content)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check Cisco IOS / IOS-XE
        if re.search(r'! Current Configuration|service timestamps|version 1[257]\.|boot-start-marker|line vty', content, re.IGNORECASE):
            result["vendor"] = "cisco"
            result["model"] = "Catalyst / ISR Series"
            result["confidence"] = 0.95
            
            v_match = re.search(r'^\s*version\s+([0-9\.]+)', content, re.MULTILINE | re.IGNORECASE)
            if v_match:
                v_num = v_match.group(1)
                result["os_version"] = f"IOS-XE {v_num}" if float(v_num.split('.')[0]) >= 16 else f"IOS {v_num}"
            
            # Model hint from header comments
            m_match = re.search(r'!\s*Current Configuration\s*-\s*([A-Za-z0-9\s/]+)', content, re.IGNORECASE)
            if m_match:
                result["model"] = m_match.group(1).split("/")[0].strip()
            
            h_match = re.search(r'^\s*hostname\s+([A-Za-z0-9\-_]+)', content, re.MULTILINE | re.IGNORECASE)
            if h_match:
                result["hostname"] = h_match.group(1)
            return result

        # Check for generic/custom appliance
        h_match = re.search(r'^\s*(?:system-id|hostname|host-name|sysname)\s+["\']?([A-Za-z0-9\-_]+)["\']?', content, re.MULTILINE | re.IGNORECASE)
        if h_match:
            result["hostname"] = h_match.group(1)
        
        return result
