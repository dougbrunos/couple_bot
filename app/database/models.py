from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from app.database.database import Base
from app.utils.date_utils import utc_now


class EventScope(str, enum.Enum):
    PERSONAL = "PERSONAL"
    PARTNER = "PARTNER"
    SHARED = "SHARED"


class RecurrenceType(str, enum.Enum):
    NONE = "NONE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class ReminderStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    CANCELLED = "CANCELLED"



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    language = Column(String(10), default="pt", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} name='{self.name}'>"


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_2_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invite_code = Column(String(32), unique=True, index=True, nullable=True)
    invite_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user_1 = relationship("User", foreign_keys=[user_1_id])
    user_2 = relationship("User", foreign_keys=[user_2_id])
    events = relationship("Event", back_populates="couple", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Couple id={self.id} user_1={self.user_1_id} user_2={self.user_2_id}>"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(Enum(EventScope), default=EventScope.PERSONAL, nullable=False)
    recurrence_type = Column(
        Enum(RecurrenceType), default=RecurrenceType.NONE, nullable=False
    )
    recurrence_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    couple = relationship("Couple", back_populates="events")
    creator = relationship("User", foreign_keys=[created_by])
    owner = relationship("User", foreign_keys=[owner_id])
    reminders = relationship(
        "Reminder", back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} title='{self.title}' start_at={self.start_at} scope={self.scope}>"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    minutes_before = Column(Integer, nullable=False, default=0)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    event = relationship("Event", back_populates="reminders")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} event_id={self.event_id} scheduled_at={self.scheduled_at} status={self.status}>"
