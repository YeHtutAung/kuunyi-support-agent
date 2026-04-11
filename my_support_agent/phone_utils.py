"""Myanmar phone number normalization."""

import re


def normalize_phone(phone: str | None) -> str | None:
    """Normalize a Myanmar phone number to 09XXXXXXXXX format.

    Returns None if the input is invalid.
    """
    if not phone:
        return None

    # Strip spaces, dashes, parentheses
    cleaned = re.sub(r"[\s\-\(\)]+", "", phone)

    # Remove +95 country code prefix → prepend 0
    if cleaned.startswith("+95"):
        cleaned = "0" + cleaned[3:]

    # Remove 959 prefix (country code without +) → replace with 09
    if cleaned.startswith("959") and len(cleaned) > 9:
        cleaned = "0" + cleaned[2:]

    # Validate: must start with 09, be 9-11 digits
    if not cleaned.startswith("09"):
        return None
    if not cleaned.isdigit():
        return None
    if len(cleaned) < 9 or len(cleaned) > 11:
        return None

    return cleaned
