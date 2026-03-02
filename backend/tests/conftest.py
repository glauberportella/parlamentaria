"""Shared test fixtures and configuration for pytest."""

import asyncio
import sqlite3
import sys
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path so agents/ package is importable from tests
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool, JSON, String, TypeDecorator, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Register UUID adapter so SQLite can bind uuid.UUID objects as strings
sqlite3.register_adapter(uuid.UUID, str)

from app.db.base import Base
from app.domain.proposicao import Proposicao
from app.domain.votacao import Votacao
from app.domain.deputado import Deputado
from app.domain.eleitor import Eleitor
from app.domain.voto_popular import VotoPopular, VotoEnum
from app.domain.analise_ia import AnaliseIA
from app.domain.evento import Evento
from app.domain.partido import Partido
from app.domain.assinatura import AssinaturaRSS, AssinaturaWebhook
from app.domain.comparativo import ComparativoVotacao
from app.domain.document_chunk import DocumentChunk  # noqa: F401


# ---------------------------------------------------------------------------
# Adapt PostgreSQL-specific types for SQLite (tests only)
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID


class _UUIDString(TypeDecorator):
    """Store UUID as a plain string in SQLite while keeping UUID semantics."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value

# Replace PostgreSQL types with SQLite-compatible equivalents before table creation
# ARRAY -> JSON (stored as JSON list), JSONB -> JSON, UUID -> String(36)
@event.listens_for(Base.metadata, "column_reflect")
def _column_reflect(inspector, table, column_info):
    pass  # pragma: no cover


def _adapt_columns_for_sqlite():
    """Monkey-patch PostgreSQL column types to SQLite-compatible types in metadata."""
    from pgvector.sqlalchemy import Vector

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, ARRAY):
                column.type = JSON()
            elif isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, PG_UUID):
                column.type = _UUIDString()
            elif isinstance(column.type, Vector):
                # pgvector Vector type → store as JSON text in SQLite
                column.type = JSON()


# ---------------------------------------------------------------------------
# In-memory SQLite async engine for tests
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop after."""
    _adapt_columns_for_sqlite()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh database session for each test."""
    async with TestSessionFactory() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with overridden dependencies."""
    from app.main import app
    from app.dependencies import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_proposicao_data() -> dict:
    """Return a dict of valid Proposicao fields."""
    return {
        "id": 12345,
        "tipo": "PL",
        "numero": 100,
        "ano": 2024,
        "ementa": "Dispõe sobre a transparência legislativa",
        "data_apresentacao": date(2024, 3, 15),
        "situacao": "Em tramitação",
        "temas": ["Transparência", "Governo"],
    }


@pytest.fixture
def sample_eleitor_data() -> dict:
    """Return a dict of valid Eleitor fields."""
    return {
        "nome": "Maria Silva",
        "email": "maria@example.com",
        "uf": "SP",
        "channel": "telegram",
        "chat_id": "12345678",
    }


@pytest.fixture
def sample_deputado_data() -> dict:
    """Return a dict of valid Deputado fields."""
    return {
        "id": 67890,
        "nome": "João Exemplo",
        "sigla_partido": "PT",
        "sigla_uf": "RJ",
        "email": "joao@camara.leg.br",
        "situacao": "Exercício",
    }


@pytest.fixture
def sample_votacao_data() -> dict:
    """Return a dict of valid Votacao fields."""
    return {
        "id": 11111,
        "proposicao_id": 12345,
        "data": datetime(2024, 6, 10, 14, 0, tzinfo=timezone.utc),
        "descricao": "Votação do PL 100/2024",
        "aprovacao": True,
        "votos_sim": 300,
        "votos_nao": 150,
        "abstencoes": 10,
    }
