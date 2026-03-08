"""Tests for EleitorService."""

import pytest
import uuid
from datetime import date

from app.domain.eleitor import Eleitor, NivelVerificacao
from app.exceptions import NotFoundException, ValidationException
from app.schemas.eleitor import EleitorCreate, EleitorUpdate
from app.services.eleitor_service import EleitorService
from app.services.validators import hash_documento


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


class TestVincularContaPorCPF:
    """Tests for vincular_conta_por_cpf (account recovery by CPF)."""

    VALID_CPF = "52998224725"

    @pytest.fixture
    async def eleitor_with_cpf(self, db_session):
        """Create a voter in the DB that has a registered CPF."""
        cpf_hashed = hash_documento(self.VALID_CPF)
        eleitor = Eleitor(
            nome="Ana Costa",
            email="ana@example.com",
            uf="SP",
            chat_id="old_chat_999",
            channel="telegram",
            cidadao_brasileiro=True,
            data_nascimento=date(1990, 1, 1),
            verificado=True,
            cpf_hash=cpf_hashed,
            nivel_verificacao=NivelVerificacao.AUTO_DECLARADO,
        )
        db_session.add(eleitor)
        await db_session.flush()
        await db_session.refresh(eleitor)
        return eleitor

    async def test_vincular_cpf_success(self, service, eleitor_with_cpf):
        """Valid CPF should find existing account and update chat_id."""
        new_chat = "new_chat_777"
        recovered, info = await service.vincular_conta_por_cpf(new_chat, self.VALID_CPF)

        assert info["vinculado"] is True
        assert recovered.id == eleitor_with_cpf.id
        assert recovered.chat_id == new_chat
        assert recovered.nome == "Ana Costa"

    async def test_vincular_cpf_formatted(self, service, eleitor_with_cpf):
        """CPF with dots/dash should also work (formatting stripped by hash)."""
        new_chat = "new_chat_888"
        recovered, info = await service.vincular_conta_por_cpf(new_chat, "529.982.247-25")

        assert info["vinculado"] is True
        assert recovered.id == eleitor_with_cpf.id
        assert recovered.chat_id == new_chat

    async def test_vincular_cpf_already_linked(self, service, eleitor_with_cpf):
        """If the account already has the same chat_id, return without changes."""
        same_chat = eleitor_with_cpf.chat_id
        recovered, info = await service.vincular_conta_por_cpf(same_chat, self.VALID_CPF)

        assert info["vinculado"] is False
        assert recovered.id == eleitor_with_cpf.id

    async def test_vincular_cpf_invalid(self, service):
        """Invalid CPF should raise ValidationException."""
        with pytest.raises(ValidationException):
            await service.vincular_conta_por_cpf("any_chat", "00000000000")

    async def test_vincular_cpf_wrong_digits(self, service):
        """CPF with wrong check digits should raise ValidationException."""
        with pytest.raises(ValidationException):
            await service.vincular_conta_por_cpf("any_chat", "52998224726")

    async def test_vincular_cpf_not_found(self, service):
        """CPF not in DB should raise NotFoundException."""
        # Use a valid CPF that isn't in the database
        with pytest.raises(NotFoundException, match="Nenhuma conta encontrada"):
            await service.vincular_conta_por_cpf("chat_123", self.VALID_CPF)

    async def test_vincular_removes_orphan_stub(self, service, db_session, eleitor_with_cpf):
        """An orphan stub for the new chat_id should be removed."""
        # Create an orphan stub (no CPF, empty name) for the new chat
        orphan = Eleitor(
            nome="",
            email=f"orphan_{uuid.uuid4().hex[:6]}@stub.com",
            uf="RJ",
            chat_id="new_chat_555",
            channel="telegram",
        )
        db_session.add(orphan)
        await db_session.flush()
        orphan_id = orphan.id

        recovered, info = await service.vincular_conta_por_cpf("new_chat_555", self.VALID_CPF)

        assert info["vinculado"] is True
        assert recovered.id == eleitor_with_cpf.id
        assert recovered.chat_id == "new_chat_555"

        # Orphan should have been deleted
        from sqlalchemy import select
        stmt = select(Eleitor).where(Eleitor.id == orphan_id)
        rows = (await db_session.execute(stmt)).scalars().all()
        assert len(rows) == 0

    async def test_vincular_rejects_when_chat_has_real_account(self, service, db_session, eleitor_with_cpf):
        """Recovery should fail if the chat_id already belongs to another real account."""
        # Create a real account for the new chat (has name and CPF)
        real = Eleitor(
            nome="Carlos Real",
            email=f"carlos_{uuid.uuid4().hex[:6]}@test.com",
            uf="MG",
            chat_id="new_chat_666",
            channel="telegram",
            cidadao_brasileiro=True,
            cpf_hash="b" * 64,  # different CPF hash
        )
        db_session.add(real)
        await db_session.flush()

        with pytest.raises(ValidationException, match="já está vinculado"):
            await service.vincular_conta_por_cpf("new_chat_666", self.VALID_CPF)
