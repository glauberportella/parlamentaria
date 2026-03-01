"""Tests for EleitorService."""

import pytest
import uuid

from app.domain.eleitor import Eleitor
from app.exceptions import NotFoundException, ValidationException
from app.schemas.eleitor import EleitorCreate, EleitorUpdate
from app.services.eleitor_service import EleitorService


@pytest.fixture
async def service(db_session):
    """Provide an EleitorService instance."""
    return EleitorService(db_session)


@pytest.fixture
async def eleitor_in_db(db_session, sample_eleitor_data):
    """Create and return a voter in the database."""
    eleitor = Eleitor(**sample_eleitor_data)
    db_session.add(eleitor)
    await db_session.flush()
    await db_session.refresh(eleitor)
    return eleitor


class TestEleitorServiceGetById:
    """Tests for get_by_id."""

    async def test_get_by_id_existing(self, service, eleitor_in_db):
        result = await service.get_by_id(eleitor_in_db.id)
        assert result.nome == "Maria Silva"

    async def test_get_by_id_not_found(self, service):
        with pytest.raises(NotFoundException):
            await service.get_by_id(uuid.uuid4())


class TestEleitorServiceGetByChatId:
    """Tests for get_by_chat_id."""

    async def test_get_by_chat_id_existing(self, service, eleitor_in_db):
        result = await service.get_by_chat_id("12345678")
        assert result is not None
        assert result.nome == "Maria Silva"

    async def test_get_by_chat_id_not_found(self, service):
        result = await service.get_by_chat_id("nonexistent")
        assert result is None


class TestEleitorServiceGetOrCreate:
    """Tests for get_or_create_by_chat_id."""

    async def test_creates_new(self, service):
        eleitor, created = await service.get_or_create_by_chat_id("new_chat_123")
        assert created is True
        assert eleitor.chat_id == "new_chat_123"
        assert eleitor.channel == "telegram"

    async def test_returns_existing(self, service, eleitor_in_db):
        eleitor, created = await service.get_or_create_by_chat_id("12345678")
        assert created is False
        assert eleitor.id == eleitor_in_db.id


class TestEleitorServiceRegister:
    """Tests for register."""

    async def test_register_new_eleitor(self, service):
        data = EleitorCreate(
            nome="João Carlos",
            email="joao@example.com",
            uf="RJ",
            chat_id="99999999",
        )
        result = await service.register(data)
        assert result.nome == "João Carlos"
        assert result.uf == "RJ"

    async def test_register_duplicate_email(self, service, eleitor_in_db):
        data = EleitorCreate(
            nome="Outra Pessoa",
            email="maria@example.com",  # Same as eleitor_in_db
            uf="MG",
            chat_id="different_chat",
        )
        with pytest.raises(ValidationException, match="já cadastrado"):
            await service.register(data)

    async def test_register_duplicate_chat_id(self, service, eleitor_in_db):
        data = EleitorCreate(
            nome="Outra Pessoa",
            email="other@example.com",
            uf="MG",
            chat_id="12345678",  # Same as eleitor_in_db
        )
        with pytest.raises(ValidationException, match="já cadastrado"):
            await service.register(data)


class TestEleitorServiceUpdateProfile:
    """Tests for update_profile."""

    async def test_update_profile(self, service, eleitor_in_db):
        data = EleitorUpdate(nome="Maria Souza", uf="MG")
        result = await service.update_profile(eleitor_in_db.id, data)
        assert result.nome == "Maria Souza"
        assert result.uf == "MG"

    async def test_update_profile_no_changes(self, service, eleitor_in_db):
        data = EleitorUpdate()
        result = await service.update_profile(eleitor_in_db.id, data)
        assert result.id == eleitor_in_db.id

    async def test_update_profile_not_found(self, service):
        data = EleitorUpdate(nome="Test")
        with pytest.raises(NotFoundException):
            await service.update_profile(uuid.uuid4(), data)


class TestEleitorServiceList:
    """Tests for list_eleitores."""

    async def test_list_empty(self, service):
        result = await service.list_eleitores()
        assert len(result) == 0

    async def test_list_with_data(self, service, eleitor_in_db):
        result = await service.list_eleitores()
        assert len(result) == 1

    async def test_list_filter_by_uf(self, service, eleitor_in_db):
        result = await service.list_eleitores(uf="SP")
        assert len(result) == 1

    async def test_list_filter_by_uf_no_match(self, service, eleitor_in_db):
        result = await service.list_eleitores(uf="AM")
        assert len(result) == 0


class TestEleitorServiceCount:
    """Tests for count."""

    async def test_count_empty(self, service):
        assert await service.count() == 0

    async def test_count_with_data(self, service, eleitor_in_db):
        assert await service.count() == 1
