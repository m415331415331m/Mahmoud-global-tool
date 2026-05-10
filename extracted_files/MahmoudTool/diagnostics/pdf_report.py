"""
diagnostics/pdf_report.py
──────────────────────────
Professional PDF report generator for device diagnostics.
Uses only Python standard library + reportlab.
Install: pip install reportlab
"""

import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def generate_report(device_info: dict, operations: list, output_path: str) -> tuple[bool, str]:
    """
    Generate a professional PDF report for a maintenance session.

    Parameters
    ----------
    device_info : dict   Keys: serial, model, brand, android_ver,
                              battery, ram, storage, knox, root, csc
    operations  : list   List of (operation, status, detail) tuples
    output_path : str    Where to save the PDF

    Returns (success, message)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle,
            Spacer, HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    except ImportError:
        # Fallback: plain text report
        return _generate_txt_report(device_info, operations, output_path)

    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # ── Header ───────────────────────────────────────────
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontSize=20,
            textColor=colors.HexColor("#1F6FEB"),
            spaceAfter=6,
            alignment=TA_CENTER,
        )
        sub_style = ParagraphStyle(
            "Sub",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#8B949E"),
            alignment=TA_CENTER,
        )

        elements.append(Paragraph("Mahmoud AI Global Tool 2026", title_style))
        elements.append(Paragraph("Device Maintenance Report", sub_style))
        elements.append(Paragraph(
            f"Date: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}",
            sub_style,
        ))
        elements.append(Spacer(1, 0.4*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F6FEB")))
        elements.append(Spacer(1, 0.4*cm))

        # ── Device Info Table ────────────────────────────────
        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#58A6FF"),
            spaceBefore=10,
            spaceAfter=6,
        )
        elements.append(Paragraph("Device Information", section_style))

        info_data = [
            ["Property", "Value"],
            ["Serial Number",   device_info.get("serial", "—")],
            ["Model",           device_info.get("model",  "—")],
            ["Brand",           device_info.get("brand",  "—")],
            ["Android Version", device_info.get("android_ver", "—")],
            ["One UI / MIUI",   device_info.get("one_ui_ver", "—")],
            ["CSC",             device_info.get("csc",    "—")],
            ["IMEI",            device_info.get("imei",   "—")],
            ["Battery",         device_info.get("battery", "—")],
            ["RAM",             device_info.get("ram",    "—")],
            ["Storage",         device_info.get("storage","—")],
            ["Knox Status",     device_info.get("knox",   "—")],
            ["Root Status",     device_info.get("root",   "—")],
            ["Bootloader",      device_info.get("bootloader", "—")],
        ]

        info_table = Table(info_data, colWidths=[6*cm, 11*cm])
        info_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1F6FEB")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#F8F9FA"), colors.white]),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",(0, 0), (-1, -1), 8),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0,0), (-1, -1), 5),
            ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))

        # ── Operations Log ───────────────────────────────────
        if operations:
            elements.append(Paragraph("Operations Performed", section_style))

            ops_data = [["#", "Operation", "Status", "Details"]]
            for i, op in enumerate(operations, 1):
                if isinstance(op, (list, tuple)) and len(op) >= 3:
                    ops_data.append([
                        str(i),
                        str(op[0])[:40],
                        str(op[1]),
                        str(op[2])[:60],
                    ])

            ops_table = Table(
                ops_data,
                colWidths=[1*cm, 6*cm, 3*cm, 7*cm],
            )
            ops_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#161B22")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, 0), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#F8F9FA"), colors.white]),
                ("FONTSIZE",    (0, 1), (-1, -1), 8),
                ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING",  (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0,0), (-1, -1), 4),
            ]))
            elements.append(ops_table)
            elements.append(Spacer(1, 0.5*cm))

        # ── Footer ───────────────────────────────────────────
        elements.append(HRFlowable(
            width="100%", thickness=0.5,
            color=colors.HexColor("#DEE2E6"),
        ))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#8B949E"),
            alignment=TA_CENTER,
            spaceBefore=6,
        )
        elements.append(Paragraph(
            "Mahmoud AI Global Tool Ultimate 2026  •  Professional Device Maintenance",
            footer_style,
        ))

        doc.build(elements)
        log.info("PDF report saved: %s", output_path)
        return True, output_path

    except Exception as exc:
        log.exception("PDF generation failed: %s", exc)
        return _generate_txt_report(device_info, operations, output_path)


def _generate_txt_report(
    device_info: dict, operations: list, output_path: str
) -> tuple[bool, str]:
    """Fallback: plain text report if reportlab is not installed."""
    txt_path = output_path.replace(".pdf", ".txt")
    try:
        lines = [
            "=" * 60,
            "  Mahmoud AI Global Tool 2026 - Maintenance Report",
            f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "DEVICE INFORMATION",
            "-" * 40,
        ]
        for k, v in device_info.items():
            lines.append(f"  {k:<20}: {v}")

        lines += ["", "OPERATIONS", "-" * 40]
        for i, op in enumerate(operations, 1):
            if isinstance(op, (list, tuple)) and len(op) >= 3:
                lines.append(f"  {i:02d}. [{op[1]}] {op[0]}: {op[2]}")

        lines += ["", "=" * 60, "  End of Report", "=" * 60]

        Path(txt_path).write_text("\n".join(lines), encoding="utf-8")
        return True, txt_path
    except Exception as exc:
        return False, str(exc)
