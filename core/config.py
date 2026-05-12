import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    telegram_bot_token: str
    database_url: str
    twilio_account_sid: Optional[str]
    twilio_auth_token: Optional[str]
    twilio_phone_number: Optional[str]
    africastalking_api_key: Optional[str]
    africastalking_username: Optional[str]
    sms_provider: str
    secret_key: str
    pin_rounds: int
    max_pin_attempts: int
    lockout_duration_minutes: int
    progressive_delay_seconds: int
    session_ttl_minutes: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./mberede.db"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
            africastalking_api_key=os.getenv("AFRICAS_TALKING_API_KEY"),
            africastalking_username=os.getenv("AFRICAS_TALKING_USERNAME"),
            sms_provider=os.getenv("SMS_PROVIDER", "twilio"),
            secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
            pin_rounds=int(os.getenv("PIN_ROUNDS", "12")),
            max_pin_attempts=int(os.getenv("MAX_PIN_ATTEMPTS", "5")),
            lockout_duration_minutes=int(os.getenv("LOCKOUT_DURATION_MINUTES", "15")),
            progressive_delay_seconds=int(os.getenv("PROGRESSIVE_DELAY_SECONDS", "2")),
            session_ttl_minutes=int(os.getenv("SESSION_TTL_MINUTES", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


config = Config.from_env()
