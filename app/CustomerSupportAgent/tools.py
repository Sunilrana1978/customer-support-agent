import hashlib
from strands import tool


@tool
def get_return_policy(product_type: str, purchase_date: str) -> dict:
    """Get the return policy for a product based on its type and purchase date.

    Args:
        product_type: Category of product (electronics, clothing, furniture, books)
        purchase_date: Purchase date in YYYY-MM-DD format

    Returns:
        Return window in days, conditions, exceptions, and how to initiate
    """
    policies = {
        "electronics": {
            "window_days": 30,
            "conditions": "Must be in original packaging with all accessories included",
            "exceptions": "Software and digital downloads are non-refundable",
        },
        "clothing": {
            "window_days": 60,
            "conditions": "Items must be unworn with original tags still attached",
            "exceptions": "Final sale items cannot be returned",
        },
        "furniture": {
            "window_days": 14,
            "conditions": "Must be disassembled and returned in original packaging",
            "exceptions": "Custom or personalized orders are non-refundable",
        },
        "books": {
            "window_days": 30,
            "conditions": "Book must be unread and in original condition",
            "exceptions": "Digital books, audiobooks, and magazines are non-refundable",
        },
    }

    policy = policies.get(
        product_type.lower(),
        {
            "window_days": 30,
            "conditions": "Standard return conditions apply",
            "exceptions": "Contact support for product-specific exceptions",
        },
    )

    return {
        "product_type": product_type,
        "purchase_date": purchase_date,
        "return_window_days": policy["window_days"],
        "conditions": policy["conditions"],
        "exceptions": policy["exceptions"],
        "how_to_return": "Log in to your account > Orders > Return Item, or contact support",
        "refund_timeline": "3-5 business days after item is received",
    }


@tool
def get_product_info(product_id: str) -> dict:
    """Get product specifications, price, and stock availability by product ID.

    Args:
        product_id: Product identifier (e.g., PROD-001, PROD-002, PROD-003)

    Returns:
        Product name, price, stock status, rating, category, and technical specs
    """
    catalog = {
        "PROD-001": {
            "name": "Wireless Noise-Canceling Headphones",
            "price": 79.99,
            "in_stock": True,
            "rating": 4.5,
            "reviews_count": 1247,
            "category": "electronics",
            "specs": {
                "battery_life": "30 hours",
                "connectivity": "Bluetooth 5.0",
                "noise_canceling": True,
                "weight": "250g",
                "driver_size": "40mm",
                "frequency_response": "20Hz - 20kHz",
            },
        },
        "PROD-002": {
            "name": "Smart Watch Series X",
            "price": 199.99,
            "in_stock": True,
            "rating": 4.7,
            "reviews_count": 3891,
            "category": "electronics",
            "specs": {
                "display": "1.9-inch AMOLED",
                "battery_life": "7 days (typical use)",
                "water_resistant": "5ATM (50m)",
                "sensors": ["heart rate", "SpO2", "GPS", "altimeter"],
                "compatibility": "iOS 14+ / Android 8+",
            },
        },
        "PROD-003": {
            "name": "Adjustable Aluminum Laptop Stand",
            "price": 49.99,
            "in_stock": False,
            "restock_date": "2026-07-01",
            "rating": 4.3,
            "reviews_count": 567,
            "category": "accessories",
            "specs": {
                "material": "Aerospace-grade aluminum",
                "height_range": "4 to 14 inches (adjustable)",
                "max_load": "10 kg",
                "laptop_size": "9 to 17 inches",
                "weight": "780g",
                "foldable": True,
            },
        },
    }

    product = catalog.get(product_id.upper())
    if not product:
        return {
            "error": f"Product '{product_id}' not found in catalog",
            "available_ids": list(catalog.keys()),
        }
    return product


@tool
def get_technical_support(product_id: str, issue_description: str) -> dict:
    """Provide troubleshooting steps and open a support ticket for a product issue.

    Args:
        product_id: Product identifier (e.g., PROD-001)
        issue_description: Clear description of the technical problem

    Returns:
        Troubleshooting steps, support ticket ID, and escalation contact
    """
    ticket_id = f"TICKET-{hashlib.md5(f'{product_id}{issue_description}'.encode()).hexdigest()[:6].upper()}"
    issue_lower = issue_description.lower()

    if any(w in issue_lower for w in ["bluetooth", "wifi", "connect", "pair", "sync", "wireless"]):
        steps = [
            "Ensure Bluetooth/WiFi is enabled and the product is within 10m of your device",
            "Power cycle the product: turn off, wait 10 seconds, then turn on",
            "Remove the product from your device's paired list and re-pair fresh",
            "Check for firmware updates in the companion app",
            "Reset to factory defaults if problem persists (hold reset button for 10s)",
        ]
    elif any(w in issue_lower for w in ["battery", "charge", "charging", "power", "dead", "drain"]):
        steps = [
            "Use the original charging cable and adapter only",
            "Charge uninterrupted for 2 hours before testing",
            "Inspect charging port for debris and clean gently with a dry toothpick",
            "Try a different power outlet or USB port",
            "Calibrate: drain battery to 0%, then charge to 100% without stopping",
        ]
    elif any(w in issue_lower for w in ["screen", "display", "dark", "bright", "flicker", "blank"]):
        steps = [
            "Force restart the device (hold power button 10-15 seconds)",
            "Adjust brightness in Settings > Display",
            "Clean the screen with a soft, lint-free, dry cloth",
            "Install any pending software or firmware updates",
            "Contact support if physical damage is present",
        ]
    elif any(w in issue_lower for w in ["sound", "audio", "mic", "microphone", "volume", "speaker"]):
        steps = [
            "Verify volume is not muted on both the product and source device",
            "Disconnect and reconnect the audio or Bluetooth connection",
            "Test with a different audio source to isolate the issue",
            "Clean the speaker grille and microphone port with a dry soft brush",
            "Reset audio settings to defaults in the companion app",
        ]
    else:
        steps = [
            "Restart the device to clear transient errors",
            "Install all pending software or firmware updates",
            "Consult the user manual section for this specific feature",
            "Perform a factory reset as a last resort (erases all settings)",
            "Contact support if hardware damage is suspected",
        ]

    return {
        "product_id": product_id,
        "issue_reported": issue_description,
        "support_ticket": ticket_id,
        "troubleshooting_steps": steps,
        "escalation_available": True,
        "support_email": "support@shopeasy.example.com",
        "support_phone": "1-800-SHOPEASY",
        "expected_response_time": "Within 24 hours on business days",
    }
