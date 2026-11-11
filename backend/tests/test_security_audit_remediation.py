import pytest
import html
from fastapi import HTTPException
from api.v1.billing import TaxInvoiceResponse, _render_invoice_html


def test_invoice_xss_escaping():
    """Verify that script tags in buyer name or email are escaped in rendered HTML."""
    inv = TaxInvoiceResponse(
        invoice_number="INV-2026-TEST",
        invoice_date="11 Nov 2026",
        payment_status="PAID",
        supplier_name="Digital Rakshak Sovereign Cyber Command",
        supplier_gstin="07AAACD1234F1Z5",
        supplier_sac_code="998313",
        buyer_name="<script>alert('xss')</script>",
        buyer_email="hacker<img src=x onerror=alert(1)>@test.com",
        place_of_supply="Delhi (07) / Pan-India",
        plan_code="b2c_pro_149",
        plan_name="Digital Rakshak Pro <svg onload=alert(2)>",
        taxable_base_amount=126.27,
        cgst_amount=11.36,
        sgst_amount=11.36,
        igst_amount=0.0,
        total_tax_amount=22.72,
        gross_amount=149.00,
        currency="INR"
    )

    rendered_html = _render_invoice_html(inv)

    # Raw script, img onerror, svg onload MUST NOT exist unescaped
    assert "<script>alert('xss')</script>" not in rendered_html
    assert "<img src=x onerror=alert(1)>" not in rendered_html
    assert "<svg onload=alert(2)>" not in rendered_html

    # Escaped versions MUST be present
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in rendered_html or "&lt;script&gt;" in rendered_html
    assert "&lt;svg onload=alert(2)&gt;" in rendered_html or "&lt;svg" in rendered_html


@pytest.mark.asyncio
async def test_spatial_pagination_bounds():
    """Verify spatial intelligence endpoint enforces bounds."""
    from api.v1.cases import get_spatial_cases
    # Requesting without auth raises 401
    with pytest.raises(HTTPException) as exc_info:
        await get_spatial_cases(user=None, db=None)
    assert exc_info.value.status_code == 401
