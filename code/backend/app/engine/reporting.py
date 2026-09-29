import io
import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)

class PDFReportGenerator:
    """
    Generates professional, enterprise-grade Network Security Compliance Audit PDF reports
    using ReportLab based on actual audit data.
    """

    @classmethod
    def generate_report(
        cls,
        device_info: Dict[str, Any],
        audit_info: Dict[str, Any],
        findings: List[Dict[str, Any]],
        output_stream: io.BytesIO
    ) -> None:
        doc = SimpleDocTemplate(
            output_stream,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom palette & styles
        title_style = ParagraphStyle(
            'CoverTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=15
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155")
        )
        mono_style = ParagraphStyle(
            'MonoText',
            parent=styles['Code'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
            fontName="Courier"
        )
        bold_cell = ParagraphStyle(
            'BoldCell',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1e293b")
        )

        elements = []

        # Header / Title Banner
        elements.append(Paragraph("NETWORK SECURITY COMPLIANCE AUDIT REPORT", title_style))
        elements.append(Paragraph("SIH 2026 AI-Driven Multi-Vendor Network Compliance Auditor", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=15))

        # Device Identification Block
        elements.append(Paragraph("1. Target Device Identification", section_heading))
        device_data = [
            [Paragraph("Hostname", bold_cell), Paragraph(device_info.get("hostname", "UNKNOWN"), body_style),
             Paragraph("Vendor", bold_cell), Paragraph(device_info.get("vendor", "UNKNOWN").upper(), body_style)],
            [Paragraph("Hardware Model", bold_cell), Paragraph(device_info.get("model", "N/A"), body_style),
             Paragraph("OS / Firmware", bold_cell), Paragraph(device_info.get("os_version", "N/A"), body_style)],
            [Paragraph("Configuration File", bold_cell), Paragraph(audit_info.get("filename", "N/A"), body_style),
             Paragraph("Audit Timestamp", bold_cell), Paragraph(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)]
        ]
        t_device = Table(device_data, colWidths=[110, 160, 110, 160])
        t_device.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_device)
        elements.append(Spacer(1, 15))

        # Executive Summary Block
        elements.append(Paragraph("2. Executive Audit Summary", section_heading))
        
        comp_pct = audit_info.get("compliance_percentage", 0.0)
        risk_score = audit_info.get("risk_score", 0.0)
        risk_level = audit_info.get("risk_level", "LOW")

        risk_color = colors.HexColor("#dc2626") if risk_level == "CRITICAL" else \
                     colors.HexColor("#ea580c") if risk_level == "HIGH" else \
                     colors.HexColor("#eab308") if risk_level == "MEDIUM" else colors.HexColor("#16a34a")

        summary_data = [
            [Paragraph("Overall Compliance Score", bold_cell), Paragraph(f"<b>{comp_pct}%</b>", body_style),
             Paragraph("Quantitative Risk Score", bold_cell), Paragraph(f"<b>{risk_score} / 100</b>", body_style)],
            [Paragraph("Overall Risk Posture", bold_cell), Paragraph(f"<b><font color='{risk_color.hexval()}'>{risk_level}</font></b>", body_style),
             Paragraph("Total Controls Evaluated", bold_cell), Paragraph(str(audit_info.get("total_controls", 0)), body_style)],
            [Paragraph("Controls Passed", bold_cell), Paragraph(f"<font color='#16a34a'><b>{audit_info.get('passed_count', 0)}</b></font>", body_style),
             Paragraph("Controls Failed", bold_cell), Paragraph(f"<font color='#dc2626'><b>{audit_info.get('failed_count', 0)}</b></font>", body_style)],
            [Paragraph("Not Configured / Evaluable", bold_cell), Paragraph(f"<font color='#64748b'><b>{audit_info.get('not_evaluable_count', 0)}</b></font>", body_style),
             Paragraph("Audit Engine Status", bold_cell), Paragraph("COMPLETED (Deterministic Rules)", body_style)]
        ]
        t_summary = Table(summary_data, colWidths=[150, 120, 150, 120])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 15))

        # Framework Compliance Breakdown
        elements.append(Paragraph("3. Multi-Framework Compliance Matrix", section_heading))
        fw_stats: Dict[str, Dict[str, int]] = {}
        for f in findings:
            fw = f.get("framework", "Unknown")
            if fw not in fw_stats:
                fw_stats[fw] = {"PASS": 0, "FAIL": 0, "NOT_EVALUABLE": 0}
            st = f.get("status", "NOT_EVALUABLE")
            if st in fw_stats[fw]:
                fw_stats[fw][st] += 1

        fw_rows = [[Paragraph("Compliance Framework", bold_cell), Paragraph("Passed", bold_cell),
                    Paragraph("Failed", bold_cell), Paragraph("Not Configured", bold_cell), Paragraph("Framework Pass Rate", bold_cell)]]
        
        for fw, counts in fw_stats.items():
            tot = counts["PASS"] + counts["FAIL"] + counts["NOT_EVALUABLE"]
            rate = round((counts["PASS"] / tot * 100), 1) if tot > 0 else 0.0
            fw_rows.append([
                Paragraph(fw, body_style),
                Paragraph(f"<font color='#16a34a'>{counts['PASS']}</font>", body_style),
                Paragraph(f"<font color='#dc2626'>{counts['FAIL']}</font>", body_style),
                Paragraph(str(counts['NOT_EVALUABLE']), body_style),
                Paragraph(f"<b>{rate}%</b>", body_style)
            ])

        t_fw = Table(fw_rows, colWidths=[180, 80, 80, 100, 100])
        t_fw.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_fw)
        elements.append(Spacer(1, 15))

        # Detailed Findings Section
        elements.append(Paragraph("4. Detailed Compliance Findings & Remediation", section_heading))
        elements.append(Paragraph("All evaluations are backed by verbatim configuration evidence line citations.", body_style))
        elements.append(Spacer(1, 8))

        # Sort findings: FAIL first, then NOT_EVALUABLE, then PASS
        sorted_findings = sorted(
            findings,
            key=lambda x: (0 if x["status"] == "FAIL" else 1 if x["status"] == "NOT_EVALUABLE" else 2)
        )

        for finding in sorted_findings:
            f_status = finding["status"]
            f_color = "#dc2626" if f_status == "FAIL" else "#64748b" if f_status == "NOT_EVALUABLE" else "#16a34a"
            sev_color = "#dc2626" if finding["severity"] == "CRITICAL" else "#ea580c" if finding["severity"] == "HIGH" else "#eab308"

            learned_tag = " <font color='#2563eb'>[Learned Mapping Applied]</font>" if finding.get("is_learned_mapping_applied") else ""

            ev_line_str = f"Line {finding['evidence_line_no']}" if finding.get("evidence_line_no") else "N/A"
            ev_text_str = finding.get("evidence_text") or "No explicit configuration line found."
            remed_str = finding.get("remediation_text") or "No remediation required."

            card_content = [
                [Paragraph(f"<b>[{finding['rule_id']}] {finding['title']}</b>{learned_tag}", bold_cell),
                 Paragraph(f"<b><font color='{f_color}'>{f_status}</font></b> | <font color='{sev_color}'>{finding['severity']}</font>", bold_cell)],
                [Paragraph(f"<b>Framework:</b> {finding['framework']} ({finding['control_id']})", body_style),
                 Paragraph(f"<b>Expected:</b> {finding['expected_value']} | <b>Detected:</b> {finding['detected_value']}", body_style)],
                [Paragraph(f"<b>Evidence ({ev_line_str}):</b><br/><font face='Courier' size='7'>{ev_text_str}</font>", body_style), ""],
            ]

            if f_status != "PASS" and finding.get("remediation_text"):
                card_content.append([
                    Paragraph(f"<b>Device-Specific Remediation Commands:</b><br/><font face='Courier' size='7'>{remed_str.replace(chr(10), '<br/>')}</font>", body_style),
                    ""
                ])

            t_card = Table(card_content, colWidths=[380, 160])
            t_card.setStyle(TableStyle([
                ('SPAN', (0, 2), (1, 2)),
                ('SPAN', (0, 3), (1, 3)) if len(card_content) > 3 else ('PADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#cbd5e1")),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))

            elements.append(t_card)
            elements.append(Spacer(1, 8))

        # Legal & Remediation Disclaimer
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        elements.append(Paragraph(
            "<b>NOTICE:</b> Recommended remediation commands must be thoroughly validated in a dedicated testing or "
            "staging environment prior to implementation in production networks. The AI-Driven Multi-Vendor Network "
            "Security Compliance Auditor never automatically modifies live network equipment.",
            ParagraphStyle('NoticeStyle', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor("#64748b"))
        ))

        doc.build(elements)
