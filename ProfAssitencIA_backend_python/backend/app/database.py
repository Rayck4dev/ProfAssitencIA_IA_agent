"""Conexão com o SQLite e base declarativa do SQLAlchemy."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_path: Path) -> Engine:
    """Cria o engine do SQLite (e a pasta do arquivo, se necessário)."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{database_path}",
        # O FastAPI executa rotas síncronas em threads diferentes.
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        # O SQLite ignora chaves estrangeiras (e o ON DELETE CASCADE) por padrão.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    """Cria as tabelas que ainda não existirem.

    Bancos criados pela versão antiga (C#/EF Core) já têm as mesmas tabelas e
    colunas, então nada é alterado neles.
    """
    import app.models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(engine)
