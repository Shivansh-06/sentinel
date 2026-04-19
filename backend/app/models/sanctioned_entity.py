import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SanctionedEntity(Base):
    __tablename__ = "sanctioned_entities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    program: Mapped[str | None] = mapped_column(String(200), nullable=True)
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_sanctioned_normalized", "normalized_name"),
        Index("ix_sanctioned_source", "source"),
    )