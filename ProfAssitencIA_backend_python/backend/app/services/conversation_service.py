"""Acesso às conversas e mensagens salvas no banco."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import DEFAULT_TITLE, ROLE_ASSISTANT, ROLE_USER, ChatTurn
from app.models import ChatMessage, Conversation, utcnow


class ConversationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_installation(self, installation_id: str) -> list[Conversation]:
        """Conversas da instalação, da mais recente para a mais antiga."""
        statement = (
            select(Conversation)
            .where(Conversation.installation_id == installation_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        )
        return list(self._db.scalars(statement))

    def get(self, conversation_id: int, installation_id: str) -> Conversation | None:
        """Busca uma conversa, apenas se ela pertencer à instalação informada."""
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.installation_id == installation_id,
        )
        return self._db.scalars(statement).first()

    def get_history(self, conversation_id: int) -> list[ChatTurn]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id)
        )
        return [ChatTurn(m.role, m.content) for m in self._db.scalars(statement)]

    def save_exchange(
        self,
        *,
        installation_id: str,
        user_message: str,
        assistant_message: str,
        conversation: Conversation | None = None,
        title: str | None = None,
    ) -> Conversation:
        """Salva a pergunta e a resposta na mesma transação.

        Se ``conversation`` for ``None``, cria uma conversa nova com o ``title``.
        """
        if conversation is None:
            conversation = Conversation(
                installation_id=installation_id,
                title=title or DEFAULT_TITLE,
            )
            self._db.add(conversation)
            self._db.flush()  # gera o id

        conversation.messages.append(ChatMessage(role=ROLE_USER, content=user_message))
        conversation.messages.append(
            ChatMessage(role=ROLE_ASSISTANT, content=assistant_message)
        )
        conversation.updated_at = utcnow()
        self._db.commit()
        return conversation

    def rename(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        conversation.updated_at = utcnow()
        self._db.commit()
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self._db.delete(conversation)  # apaga as mensagens em cascata
        self._db.commit()
