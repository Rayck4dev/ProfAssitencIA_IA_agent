"""Entidades persistidas no SQLite.

Os nomes de tabelas e colunas são os mesmos que o Entity Framework Core criava na
versão em C#, para que um ``profassistenc.db`` antigo continue funcionando.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Data/hora atual em UTC, sem fuso (formato guardado no banco)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Conversation(Base):
    __tablename__ = "Conversations"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column("Title", Text, nullable=True)
    installation_id: Mapped[str] = mapped_column("InstallationId", Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt", DateTime, nullable=False, default=utcnow
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "MessageEntities"

    id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        "ConversationId",
        Integer,
        ForeignKey("Conversations.Id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column("Role", Text, nullable=False)
    content: Mapped[str] = mapped_column("Content", Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
