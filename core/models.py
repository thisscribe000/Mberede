import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Column,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
    Session,
    configure_mappers,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    pin_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    silent_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    contacts = relationship("EmergencyContact", back_populates="user", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="user", cascade="all, delete-orphan")
    sos_logs = relationship("SOSLog", back_populates="user", cascade="all, delete-orphan")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    relationship_ = Column(String(100), nullable=True)
    priority = Column(Integer, default=1)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(6), nullable=True)
    verification_expires = Column(DateTime, nullable=True)
    consent_obtained = Column(Boolean, default=False)
    consent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="contacts")


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    accessor_telegram_id = Column(BigInteger, nullable=True)
    action = Column(String(50), nullable=False)
    contact_id = Column(String(36), ForeignKey("emergency_contacts.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=False)

    user = relationship("User", back_populates="access_logs")


class SOSLog(Base):
    __tablename__ = "sos_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(String(36), ForeignKey("emergency_contacts.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered = Column(Boolean, default=False)
    twilio_sid = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sos_logs")


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(8), nullable=False)
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionOverride(Base):
    __tablename__ = "session_overrides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    original_user_id = Column(String(36), nullable=False)
    guest_user_id = Column(String(36), nullable=False)
    switched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


_engine = None
_SessionLocal = None
_async_engine = None
_AsyncSessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = config.database_url
        if url.startswith("postgresql"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        _engine = create_engine(url, echo=False)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def init_db():
    configure_mappers()
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_db() -> Session:
    return get_session_factory()()


async def get_async_db() -> AsyncSession:
    global _async_engine, _AsyncSessionLocal
    if _async_engine is None:
        if config.database_url.startswith("sqlite"):
            _async_engine = create_async_engine("sqlite+aiosqlite:///./mberede.db", echo=False)
        else:
            _async_engine = create_async_engine(config.database_url, echo=False)

    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(bind=_async_engine, expire_on_commit=False, class_=AsyncSession)

    async with _AsyncSessionLocal() as session:
        yield session
