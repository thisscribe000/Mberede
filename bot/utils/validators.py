import re
import phonenumbers
from typing import Tuple


def validate_pin(pin: str) -> Tuple[bool, str]:
    if not pin:
        return False, "PIN cannot be empty."
    if not re.match(r"^\d{4,6}$", pin):
        return False, "PIN must be 4 to 6 digits."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str, str]:
    try:
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(parsed):
            return False, "Invalid phone number.", ""
        return True, "", phonenumbers.format_number(parsed, phonenumbers.E164_E.164)
    except phonenumbers.NumberParseException:
        return False, "Could not parse phone number. Include country code (e.g. +234).", ""


def validate_name(name: str) -> Tuple[bool, str]:
    stripped = name.strip()
    if not stripped:
        return False, "Name cannot be empty."
    if len(stripped) < 2:
        return False, "Name is too short."
    if len(stripped) > 100:
        return False, "Name is too long."
    if not re.match(r"^[a-zA-Z0-9\s\-\.\']+$", stripped):
        return False, "Name contains invalid characters."
    return True, ""


def sanitize_input(text: str) -> str:
    return re.sub(r"[<>&\"']", "", text.strip())
