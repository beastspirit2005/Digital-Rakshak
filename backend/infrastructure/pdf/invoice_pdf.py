"""
Digital Rakshak GST Tax Invoice PDF Generator
==============================================
Generates publication-quality, mobile-compatible A4 PDF tax invoices
compliant with Section 31 of the CGST Act, 2017 and SAC 998313.
"""

from __future__ import annotations

import io
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_invoice_pdf(
    invoice_number: str,
    invoice_date: str,
    buyer_name: str,
    buyer_email: str,
    plan_name: str,
    taxable_base: float,
    cgst: float,
    sgst: float,
    total_tax: float,
    gross_amount: float,
    currency: str = "INR",
    supplier_name: str = "Digital Rakshak Cyber Defense Core Pvt. Ltd.",
    supplier_gstin: str = "07AABCD1234E1Z5",
    supplier_sac_code: str = "998313",
    payment_status: str = "PAID",
) -> bytes:
    """
    Renders an official, print-ready GST Tax Invoice into in-memory PDF bytes.
    Compatible with native PDF viewers on iOS, Android, and Desktop.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )

    badge_style = ParagraphStyle(
        "DocBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        alignment=2,
        textColor=colors.HexColor("#0284c7"),
    )

    label_style = ParagraphStyle(
        "BlockLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )

    body_style = ParagraphStyle(
        "BlockBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph(
                "<b>DIGITAL RAKSHAK</b><br/>"
                "<font color='#64748b' size=7>NATIONAL CYBER DEFENSE CORE &bull; INDIA</font>",
                title_style,
            ),
            Paragraph(
                "<font size=16 color='#0284c7'><b>TAX INVOICE</b></font><br/>"
                f"<font size=8 color='#059669'><b>STATUS: {payment_status} &bull; SAC {supplier_sac_code}</b></font>",
                badge_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[310, 210])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header_table)
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#0284c7"),
            spaceAfter=14,
        )
    )

    # 2. Supplier & Customer Information Blocks
    info_data = [
        [
            Paragraph("<b>SUPPLIER DETAILS (ISSUER)</b>", label_style),
            Paragraph("<b>INVOICE & BUYER DETAILS</b>", label_style),
        ],
        [
            Paragraph(
                f"<b>{supplier_name}</b><br/>"
                "Cyber Defense Complex, Tech Zone 4<br/>"
                "New Delhi, India — 110001<br/>"
                f"<b>GSTIN:</b> {supplier_gstin}<br/>"
                f"<b>SAC Code:</b> {supplier_sac_code} (Cybersecurity Threat Intel & Software)",
                body_style,
            ),
            Paragraph(
                f"<b>Invoice Number:</b> {invoice_number}<br/>"
                f"<b>Invoice Date:</b> {invoice_date}<br/>"
                f"<b>Billed To:</b> {buyer_name}<br/>"
                f"<b>Email:</b> {buyer_email}<br/>"
                "<b>Place of Supply:</b> Delhi (07) / Pan-India",
                body_style,
            ),
        ],
    ]
    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 14))

    # 3. Itemized Services Table
    table_data = [
        [
            Paragraph("<b>Description of Services</b>", label_style),
            Paragraph("<b>SAC</b>", label_style),
            Paragraph("<b>Qty</b>", label_style),
            Paragraph("<b>Taxable Value</b>", ParagraphStyle("R1", parent=label_style, alignment=2)),
            Paragraph("<b>CGST (9%)</b>", ParagraphStyle("R2", parent=label_style, alignment=2)),
            Paragraph("<b>SGST (9%)</b>", ParagraphStyle("R3", parent=label_style, alignment=2)),
            Paragraph(f"<b>Total ({currency})</b>", ParagraphStyle("R4", parent=label_style, alignment=2)),
        ],
        [
            Paragraph(
                f"<b>{plan_name}</b><br/>"
                "<font size=7 color='#64748b'>Continuous Zero-Day AI Defense, Attack DNA Deconstruction & Threat Graph</font>",
                body_style,
            ),
            Paragraph(supplier_sac_code, body_style),
            Paragraph("1", body_style),
            Paragraph(f"Rs. {taxable_base:.2f}", ParagraphStyle("RB1", parent=body_style, alignment=2)),
            Paragraph(f"Rs. {cgst:.2f}", ParagraphStyle("RB2", parent=body_style, alignment=2)),
            Paragraph(f"Rs. {sgst:.2f}", ParagraphStyle("RB3", parent=body_style, alignment=2)),
            Paragraph(f"<b>Rs. {gross_amount:.2f}</b>", ParagraphStyle("RB4", parent=body_style, alignment=2)),
        ],
    ]
    items_table = Table(table_data, colWidths=[170, 45, 30, 75, 65, 65, 70])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 14))

    # 4. Summary Totals Box
    summary_data = [
        [
            Paragraph("Taxable Base Amount:", body_style),
            Paragraph(f"Rs. {taxable_base:.2f}", ParagraphStyle("S1", parent=body_style, alignment=2)),
        ],
        [
            Paragraph("Central GST (CGST @ 9%):", body_style),
            Paragraph(f"Rs. {cgst:.2f}", ParagraphStyle("S2", parent=body_style, alignment=2)),
        ],
        [
            Paragraph("State GST (SGST @ 9%):", body_style),
            Paragraph(f"Rs. {sgst:.2f}", ParagraphStyle("S3", parent=body_style, alignment=2)),
        ],
        [
            Paragraph("Total GST Tax (18%):", body_style),
            Paragraph(f"Rs. {total_tax:.2f}", ParagraphStyle("S4", parent=body_style, alignment=2)),
        ],
        [
            Paragraph("<b>Total Invoice Amount:</b>", body_style),
            Paragraph(f"<b>Rs. {gross_amount:.2f}</b>", ParagraphStyle("S5", parent=body_style, alignment=2)),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[140, 95])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#0284c7")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    wrap_table = Table([["", summary_table]], colWidths=[285, 235])
    wrap_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story.append(wrap_table)
    story.append(Spacer(1, 16))

    # 5. Declarations & Digital Signature Seal
    footer_text = Paragraph(
        "<font size=7 color='#64748b'>"
        "<b>Terms & Declarations:</b><br/>"
        "1. This is a computer-generated tax invoice issued in compliance with the Central Goods and Services Tax Act, 2017.<br/>"
        "2. Supply covered under SAC 998313 (Cybersecurity threat intelligence and cloud SaaS defense services).<br/>"
        "3. Payment received electronically via Razorpay UPI AutoPay / Credit / Debit Card.<br/>"
        "4. Supply of service is not liable for Reverse Charge (RCM: No).<br/>"
        "Digital Rakshak Cyber Defense Core Pvt. Ltd. &bull; CIN: U72900DL2026PTC123456 &bull; Authorized Electronic Signature & Seal"
        "</font>",
        body_style,
    )
    story.append(footer_text)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
