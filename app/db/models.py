from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.constants import DEFAULT_DEPTH


class Base(DeclarativeBase):
    """Base declarative class for database models."""


class User(Base):
    """Telegram user with compact per-user bot settings."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    search_depth: Mapped[int] = mapped_column(Integer, default=DEFAULT_DEPTH)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SearchRequest(Base):
    """Saved valid search request with a compact result preview."""

    __tablename__ = "search_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    search_type: Mapped[str] = mapped_column(String(20), index=True)
    original_query: Mapped[str] = mapped_column(String(255))
    normalized_query: Mapped[str] = mapped_column(String(255))
    result_status: Mapped[str] = mapped_column(String(32), default="готово")
    short_result_preview: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
