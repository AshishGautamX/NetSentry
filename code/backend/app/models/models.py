import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), index=True, default="UNKNOWN-DEVICE")
    vendor = Column(String(100), index=True, default="Generic")
    model = Column(String(100), default="Unknown Model")
    os_version = Column(String(100), default="Unknown OS")
    serial_number = Column(String(100), default="N/A")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    audits = relationship("AuditRun", back_populates="device", cascade="all, delete-orphan")


class Configuration(Base):
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)
    raw_content = Column(Text, nullable=False)
    sanitized_content = Column(Text, nullable=False)
    vendor_detected = Column(String(100), default="unknown")
    device_model_detected = Column(String(100), default="unknown")
    os_detected = Column(String(100), default="unknown")
    file_size = Column(Integer, default=0)
    lines_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    lines = relationship("ConfigurationLine", back_populates="configuration", cascade="all, delete-orphan")
    audits = relationship("AuditRun", back_populates="configuration", cascade="all, delete-orphan")
    unknown_commands = relationship("UnknownCommand", back_populates="configuration", cascade="all, delete-orphan")


class ConfigurationLine(Base):
    __tablename__ = "configuration_lines"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("configurations.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    section_context = Column(String(255), default="")
    is_security_relevant = Column(Boolean, default=False)
    normalized_param = Column(String(255), nullable=True)

    configuration = relationship("Configuration", back_populates="lines")


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    config_id = Column(Integer, ForeignKey("configurations.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    compliance_percentage = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(50), default="UNKNOWN")  # CRITICAL, HIGH, MEDIUM, LOW
    
    total_controls = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    not_evaluable_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)
    
    normalized_baseline = Column(JSON, default=dict)
    status = Column(String(50), default="COMPLETED")

    device = relationship("Device", back_populates="audits")
    configuration = relationship("Configuration", back_populates="audits")
    findings = relationship("AuditFinding", back_populates="audit", cascade="all, delete-orphan")


class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=False)
    rule_id = Column(String(100), index=True, nullable=False)
    framework = Column(String(50), index=True, nullable=False)
    control_id = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    
    status = Column(String(50), nullable=False)  # PASS, FAIL, NOT_EVALUABLE, UNKNOWN
    severity = Column(String(50), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    
    normalized_param = Column(String(255), nullable=False)
    detected_value = Column(String(255), nullable=True)
    expected_value = Column(String(255), nullable=True)
    
    evidence_line_no = Column(Integer, nullable=True)
    evidence_text = Column(Text, nullable=True)
    section_context = Column(String(255), default="")
    rationale = Column(Text, nullable=True)
    
    remediation_text = Column(Text, nullable=True)
    verification_cmd = Column(String(255), nullable=True)
    is_learned_mapping_applied = Column(Boolean, default=False)

    audit = relationship("AuditRun", back_populates="findings")


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), unique=True, index=True, nullable=False)
    framework = Column(String(50), index=True, nullable=False)
    framework_version = Column(String(50), default="")
    control_id = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    parameter = Column(String(255), index=True, nullable=False)
    operator = Column(String(50), nullable=False)
    expected_value = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    category = Column(String(100), default="General")
    rationale = Column(Text, nullable=True)


class LearnedMapping(Base):
    __tablename__ = "learned_mappings"

    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(String(100), index=True, nullable=False)
    command_pattern = Column(String(255), nullable=False)
    normalized_param = Column(String(255), index=True, nullable=False)
    semantic_category = Column(String(100), default="General")
    value_type = Column(String(50), default="string")  # int, boolean_true, boolean_false, string, eval_*
    extraction_regex = Column(String(255), nullable=True)
    description = Column(Text, default="")
    source = Column(String(100), default="HUMAN_TRAINING")  # HUMAN_TRAINING, SEEDED, AI_DISCOVERY
    confidence = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)


class UnknownCommand(Base):
    __tablename__ = "unknown_commands"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("configurations.id"), nullable=False)
    raw_command = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=False)
    vendor = Column(String(100), default="unknown")
    ai_suggested_category = Column(String(100), default="Uncategorized")
    ai_suggested_param = Column(String(255), default="")
    ai_confidence = Column(Float, default=0.5)
    status = Column(String(50), default="PENDING")  # PENDING, MAPPED, IGNORED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    configuration = relationship("Configuration", back_populates="unknown_commands")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
