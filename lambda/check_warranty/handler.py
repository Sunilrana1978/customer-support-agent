"""
Tool 5: check_warranty — AgentCore Gateway Lambda target.
Returns warranty status, expiry, and coverage details for a product.
"""

from datetime import datetime, timedelta


WARRANTY_DB = {
    "PROD-001": {"period_months": 24, "type": "Limited Manufacturer Warranty"},
    "PROD-002": {"period_months": 12, "type": "Limited Manufacturer Warranty"},
    "PROD-003": {"period_months": 36, "type": "Structural Warranty"},
}


def handler(event, context):
    """Check whether a product is under warranty."""
    product_id = event.get("product_id", "").upper().strip()
    purchase_date_str = event.get("purchase_date", "").strip()
    serial_number = event.get("serial_number", "N/A")

    if not product_id or not purchase_date_str:
        return {"error": "product_id and purchase_date are required"}

    warranty = WARRANTY_DB.get(product_id)
    if not warranty:
        return {
            "product_id": product_id,
            "status": "unknown",
            "message": f"No warranty record found for product {product_id}",
        }

    try:
        purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid purchase_date '{purchase_date_str}'. Use YYYY-MM-DD format."}

    warranty_end = purchase_date + timedelta(days=warranty["period_months"] * 30)
    today = datetime.now()
    is_active = today <= warranty_end
    days_remaining = max(0, (warranty_end - today).days)

    return {
        "product_id": product_id,
        "serial_number": serial_number,
        "purchase_date": purchase_date_str,
        "warranty_type": warranty["type"],
        "warranty_period_months": warranty["period_months"],
        "warranty_expiry": warranty_end.strftime("%Y-%m-%d"),
        "status": "active" if is_active else "expired",
        "days_remaining": days_remaining if is_active else 0,
        "coverage": "Manufacturing defects and hardware failures (excludes accidental damage)",
        "how_to_claim": "Email support@shopeasy.example.com with your ticket number and proof of purchase",
    }
