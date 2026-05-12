import re
import hmac
import hashlib
import bcrypt
from datetime import datetime, timedelta

from core.config import config


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=config.pin_rounds)).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())


def generate_session_token() -> str:
    import uuid
    return str(uuid.uuid4())


def is_account_locked(locked_until: datetime | None) -> bool:
    if locked_until is None:
        return False
    return datetime.utcnow() < locked_until


def get_lockout_duration(failed_attempts: int) -> timedelta:
    if failed_attempts >= 20:
        return timedelta(hours=24)
    elif failed_attempts >= 10:
        return timedelta(hours=1)
    elif failed_attempts >= 5:
        return timedelta(minutes=config.lockout_duration_minutes)
    return timedelta(minutes=config.lockout_duration_minutes)


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def generate_recovery_code() -> str:
    import secrets
    return secrets.token_hex(4).upper()
