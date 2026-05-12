from datetime import datetime
from core.models import User, SessionOverride, get_db


def get_active_user(telegram_user_id: int):
    db = get_db()
    override = db.query(SessionOverride).filter(
        SessionOverride.telegram_user_id == telegram_user_id,
        SessionOverride.expires_at > datetime.utcnow(),
    ).first()

    if override:
        user = db.query(User).filter(User.id == override.guest_user_id).first()
        return user, override

    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    return user, None


def is_switched(telegram_user_id: int) -> bool:
    _, override = get_active_user(telegram_user_id)
    return override is not None
