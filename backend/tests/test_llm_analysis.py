"""Tests for LLMAnalysisService, generate_analysis_task, and admin endpoints."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.proposicao import Proposicao
from app.schemas.analise_ia import AnaliseIACreate
from app.services.analise_service import AnaliseIAService
from app.services.llm_analysis_service import LLMAnalysisError, LLMAnalysisService


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_LLM_RESPONSE = {
    "resumo_leigo": "Esta proposição visa aumentar a transparência do governo.",
    "impacto_esperado": "Maior acesso à informação pública pelos cidadãos.",
    "areas_afetadas": ["Transparência", "Governo"],
    "argumentos_favor": [
        "Mais transparência nas contas públicas",
        "Controle social fortalecido",
        "Redução de corrupção",
    ],
    "argumentos_contra": [
        "Custo de implementação elevado",
        "Possível sobrecarga dos órgãos públicos",
        "Risco de exposição de dados sensíveis",
    ],
}


@pytest.fixture
def sample_prop_data():
    """Return sample proposition data dict for LLM analysis."""
    return {
        "id": 12345,
        "tipo": "PL",
        "numero": 100,
        "ano": 2024,
        "ementa": "Dispõe sobre a transparência legislativa",
        "situacao": "Em tramitação",
        "temas": ["Transparência", "Governo"],
        "autores": [{"nome": "Dep. João Silva"}],
    }


# ---------------------------------------------------------------------------
# LLMAnalysisService — Unit Tests
# ---------------------------------------------------------------------------


class TestLLMAnalysisServiceBuildPrompt:
    """Tests for _build_prompt."""

    def test_builds_prompt_with_all_fields(self, sample_prop_data):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        prompt = service._build_prompt(sample_prop_data)
        assert "PL 100/2024" in prompt
        assert "transparência legislativa" in prompt
        assert "Em tramitação" in prompt
        assert "Transparência, Governo" in prompt
        assert "Dep. João Silva" in prompt

    def test_builds_prompt_with_missing_optional_fields(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        prompt = service._build_prompt({"tipo": "PEC", "numero": 1, "ano": 2025, "ementa": "Teste"})
        assert "PEC 1/2025" in prompt
        assert "Não informado" in prompt  # temas and autores missing

    def test_builds_prompt_with_dict_autores(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        data = {"tipo": "PL", "numero": 1, "ano": 2025, "ementa": "T", "autores": {"nome": "Fulano"}}
        prompt = service._build_prompt(data)
        assert "Fulano" in prompt

    def test_builds_prompt_with_empty_temas(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        data = {"tipo": "PL", "numero": 1, "ano": 2025, "ementa": "T", "temas": []}
        prompt = service._build_prompt(data)
        assert "Não informado" in prompt


class TestLLMAnalysisServiceValidate:
    """Tests for _validate_and_normalize."""

    def test_valid_response(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        result = service._validate_and_normalize(SAMPLE_LLM_RESPONSE, 123)
        assert result["resumo_leigo"] == SAMPLE_LLM_RESPONSE["resumo_leigo"]
        assert len(result["areas_afetadas"]) == 2
        assert len(result["argumentos_favor"]) == 3

    def test_missing_required_field_raises(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        incomplete = {"resumo_leigo": "ok"}  # missing other fields
        with pytest.raises(LLMAnalysisError, match="Campo obrigatório"):
            service._validate_and_normalize(incomplete, 123)

    def test_caps_areas_at_5(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        data = {
            **SAMPLE_LLM_RESPONSE,
            "areas_afetadas": ["a1", "a2", "a3", "a4", "a5", "a6", "a7"],
        }
        result = service._validate_and_normalize(data, 123)
        assert len(result["areas_afetadas"]) == 5

    def test_caps_argumentos_at_5(self):
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake")
        data = {
            **SAMPLE_LLM_RESPONSE,
            "argumentos_favor": ["a1", "a2", "a3", "a4", "a5", "a6"],
        }
        result = service._validate_and_normalize(data, 123)
        assert len(result["argumentos_favor"]) == 5


class TestLLMAnalysisServiceAnalyze:
    """Tests for analyze_proposition (mocking genai client)."""

    @pytest.fixture
    def mock_service(self):
        """Create LLMAnalysisService with mocked genai client."""
        service = LLMAnalysisService(model="gemini-2.0-flash", api_key="fake-key")
        service._client = MagicMock()
        return service

    async def test_successful_analysis(self, mock_service, sample_prop_data):
        mock_response = MagicMock()
        mock_response.text = json.dumps(SAMPLE_LLM_RESPONSE)
        mock_service._client.models.generate_content.return_value = mock_response

        result = await mock_service.analyze_proposition(sample_prop_data)
        assert result["resumo_leigo"] == SAMPLE_LLM_RESPONSE["resumo_leigo"]
        assert result["impacto_esperado"] == SAMPLE_LLM_RESPONSE["impacto_esperado"]
        assert len(result["argumentos_favor"]) == 3
        mock_service._client.models.generate_content.assert_called_once()

    async def test_api_error_raises_llm_error(self, mock_service, sample_prop_data):
        mock_service._client.models.generate_content.side_effect = RuntimeError("API down")
        with pytest.raises(LLMAnalysisError, match="Falha ao chamar LLM"):
            await mock_service.analyze_proposition(sample_prop_data)

    async def test_empty_response_raises_llm_error(self, mock_service, sample_prop_data):
        mock_response = MagicMock()
        mock_response.text = ""
        mock_service._client.models.generate_content.return_value = mock_response
        with pytest.raises(LLMAnalysisError, match="resposta vazia"):
            await mock_service.analyze_proposition(sample_prop_data)

    async def test_invalid_json_raises_llm_error(self, mock_service, sample_prop_data):
        mock_response = MagicMock()
        mock_response.text = "not json at all"
        mock_service._client.models.generate_content.return_value = mock_response
        with pytest.raises(LLMAnalysisError, match="não é JSON válido"):
            await mock_service.analyze_proposition(sample_prop_data)

    async def test_json_in_markdown_code_block(self, mock_service, sample_prop_data):
        """LLM sometimes wraps JSON in markdown code blocks."""
        mock_response = MagicMock()
        mock_response.text = f"```json\n{json.dumps(SAMPLE_LLM_RESPONSE)}\n```"
        mock_service._client.models.generate_content.return_value = mock_response

        result = await mock_service.analyze_proposition(sample_prop_data)
        assert result["resumo_leigo"] == SAMPLE_LLM_RESPONSE["resumo_leigo"]

    async def test_missing_field_in_response_raises(self, mock_service, sample_prop_data):
        incomplete = {"resumo_leigo": "ok", "impacto_esperado": "ok"}
        mock_response = MagicMock()
        mock_response.text = json.dumps(incomplete)
        mock_service._client.models.generate_content.return_value = mock_response
        with pytest.raises(LLMAnalysisError, match="Campo obrigatório"):
            await mock_service.analyze_proposition(sample_prop_data)


# ---------------------------------------------------------------------------
# generate_analysis_task — Unit Tests (mock DB + LLM)
# Tests use sync `def` to avoid event loop conflicts with asyncio.run()
# inside the task. All async services/sessions are fully mocked.
# ---------------------------------------------------------------------------


class TestGenerateAnalysisTask:
    """Tests for the Celery generate_analysis_task."""

    @patch("app.tasks.generate_analysis.get_async_session")
    def test_analyzes_single_proposition(self, mock_session_ctx):
        """Test analyzing a single proposition by ID."""
        from app.tasks.generate_analysis import generate_analysis_task

        mock_session = MagicMock()
        # begin_nested() must return an async context manager (not a coroutine)
        mock_nested = AsyncMock()
        mock_session.begin_nested.return_value = mock_nested
        # commit/rollback are async
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        # Mock ProposicaoService
        mock_prop = MagicMock()
        mock_prop.id = 12345
        mock_prop.tipo = "PL"
        mock_prop.numero = 100
        mock_prop.ano = 2024
        mock_prop.ementa = "Teste"
        mock_prop.situacao = "Em tramitação"
        mock_prop.temas = ["Saúde"]
        mock_prop.autores = None

        with (
            patch("app.services.proposicao_service.ProposicaoService") as MockPropService,
            patch("app.services.analise_service.AnaliseIAService") as MockAnaliseService,
            patch("app.services.llm_analysis_service.LLMAnalysisService") as MockLLM,
        ):
            mock_prop_svc = AsyncMock()
            mock_prop_svc.get_by_id = AsyncMock(return_value=mock_prop)
            MockPropService.return_value = mock_prop_svc

            mock_analise_svc = AsyncMock()
            mock_analise_svc.create_analysis = AsyncMock()
            MockAnaliseService.return_value = mock_analise_svc

            mock_llm = AsyncMock()
            mock_llm.analyze_proposition = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)
            MockLLM.return_value = mock_llm

            result = generate_analysis_task(proposicao_id=12345)

        assert result["analysed"] == 1
        assert result["errors"] == 0
        mock_llm.analyze_proposition.assert_called_once()

    @patch("app.tasks.generate_analysis.get_async_session")
    def test_analyzes_all_pending(self, mock_session_ctx):
        """Test analyzing all propositions without existing analysis."""
        from app.tasks.generate_analysis import generate_analysis_task

        mock_session = MagicMock()
        mock_nested = AsyncMock()
        mock_session.begin_nested.return_value = mock_nested
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_prop = MagicMock()
        mock_prop.id = 12345
        mock_prop.tipo = "PL"
        mock_prop.numero = 100
        mock_prop.ano = 2024
        mock_prop.ementa = "Teste"
        mock_prop.situacao = "Em tramitação"
        mock_prop.temas = []
        mock_prop.autores = None

        with (
            patch("app.services.proposicao_service.ProposicaoService") as MockPropService,
            patch("app.services.analise_service.AnaliseIAService") as MockAnaliseService,
            patch("app.services.llm_analysis_service.LLMAnalysisService") as MockLLM,
        ):
            mock_prop_svc = AsyncMock()
            mock_prop_svc.list_proposicoes = AsyncMock(return_value=[mock_prop])
            MockPropService.return_value = mock_prop_svc

            mock_analise_svc = AsyncMock()
            mock_analise_svc.get_latest = AsyncMock(return_value=None)  # No existing analysis
            mock_analise_svc.create_analysis = AsyncMock()
            MockAnaliseService.return_value = mock_analise_svc

            mock_llm = AsyncMock()
            mock_llm.analyze_proposition = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)
            MockLLM.return_value = mock_llm

            result = generate_analysis_task()  # No proposicao_id

        assert result["analysed"] == 1
        assert result["errors"] == 0

    @patch("app.tasks.generate_analysis.get_async_session")
    def test_skips_already_analyzed(self, mock_session_ctx):
        """Test that already-analyzed propositions are skipped."""
        from app.tasks.generate_analysis import generate_analysis_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_prop = MagicMock()
        mock_prop.id = 12345

        with (
            patch("app.services.proposicao_service.ProposicaoService") as MockPropService,
            patch("app.services.analise_service.AnaliseIAService") as MockAnaliseService,
            patch("app.services.llm_analysis_service.LLMAnalysisService") as MockLLM,
        ):
            mock_prop_svc = AsyncMock()
            mock_prop_svc.list_proposicoes = AsyncMock(return_value=[mock_prop])
            MockPropService.return_value = mock_prop_svc

            mock_existing = MagicMock()  # Existing analysis
            mock_analise_svc = AsyncMock()
            mock_analise_svc.get_latest = AsyncMock(return_value=mock_existing)
            MockAnaliseService.return_value = mock_analise_svc

            mock_llm = AsyncMock()
            MockLLM.return_value = mock_llm

            result = generate_analysis_task()  # No ID — analyze all pending

        assert result["analysed"] == 0
        mock_llm.analyze_proposition.assert_not_called()

    @patch("app.tasks.generate_analysis.get_async_session")
    def test_handles_llm_error_gracefully(self, mock_session_ctx):
        """Test that LLM errors don't crash the task."""
        from app.tasks.generate_analysis import generate_analysis_task

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_ctx.return_value = mock_ctx

        mock_prop = MagicMock()
        mock_prop.id = 12345
        mock_prop.tipo = "PL"
        mock_prop.numero = 100
        mock_prop.ano = 2024
        mock_prop.ementa = "Teste"
        mock_prop.situacao = "Em tramitação"
        mock_prop.temas = []
        mock_prop.autores = None

        with (
            patch("app.services.proposicao_service.ProposicaoService") as MockPropService,
            patch("app.services.analise_service.AnaliseIAService") as MockAnaliseService,
            patch("app.services.llm_analysis_service.LLMAnalysisService") as MockLLM,
        ):
            mock_prop_svc = AsyncMock()
            mock_prop_svc.get_by_id = AsyncMock(return_value=mock_prop)
            MockPropService.return_value = mock_prop_svc

            mock_analise_svc = AsyncMock()
            MockAnaliseService.return_value = mock_analise_svc

            mock_llm = AsyncMock()
            mock_llm.analyze_proposition = AsyncMock(
                side_effect=LLMAnalysisError("API down")
            )
            MockLLM.return_value = mock_llm

            result = generate_analysis_task(proposicao_id=12345)

        assert result["analysed"] == 0
        assert result["errors"] == 1


# ---------------------------------------------------------------------------
# Integration: AnaliseIAService + LLMAnalysisService persistence
# ---------------------------------------------------------------------------


class TestAnalysisIntegration:
    """Integration tests: LLM result → AnaliseIAService → DB."""

    @pytest.fixture
    async def proposicao(self, db_session, sample_proposicao_data):
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()
        await db_session.refresh(prop)
        return prop

    async def test_llm_result_persisted_correctly(self, db_session, proposicao):
        """Test that LLM analysis result is correctly saved via AnaliseIAService."""
        analise_service = AnaliseIAService(db_session)

        create_data = AnaliseIACreate(
            proposicao_id=proposicao.id,
            resumo_leigo=SAMPLE_LLM_RESPONSE["resumo_leigo"],
            impacto_esperado=SAMPLE_LLM_RESPONSE["impacto_esperado"],
            areas_afetadas=SAMPLE_LLM_RESPONSE["areas_afetadas"],
            argumentos_favor=SAMPLE_LLM_RESPONSE["argumentos_favor"],
            argumentos_contra=SAMPLE_LLM_RESPONSE["argumentos_contra"],
            provedor_llm="google",
            modelo="gemini-2.0-flash",
        )

        result = await analise_service.create_analysis(create_data)
        assert result.versao == 1
        assert result.resumo_leigo == SAMPLE_LLM_RESPONSE["resumo_leigo"]
        assert result.provedor_llm == "google"

        # Verify proposicao.resumo_ia was updated
        from app.repositories.proposicao import ProposicaoRepository
        prop_repo = ProposicaoRepository(db_session)
        updated_prop = await prop_repo.get_by_id(proposicao.id)
        assert updated_prop.resumo_ia == SAMPLE_LLM_RESPONSE["resumo_leigo"]

    async def test_re_analysis_increments_version(self, db_session, proposicao):
        """Test that re-analyzing creates a new version."""
        analise_service = AnaliseIAService(db_session)

        create_data = AnaliseIACreate(
            proposicao_id=proposicao.id,
            resumo_leigo="Versão 1",
            impacto_esperado="Impacto v1",
            areas_afetadas=["Saúde"],
            argumentos_favor=["Pró 1"],
            argumentos_contra=["Contra 1"],
            provedor_llm="google",
            modelo="gemini-2.0-flash",
        )

        v1 = await analise_service.create_analysis(create_data)
        assert v1.versao == 1

        create_data_v2 = AnaliseIACreate(
            proposicao_id=proposicao.id,
            resumo_leigo="Versão 2 — atualizada",
            impacto_esperado="Impacto v2",
            areas_afetadas=["Saúde", "Educação"],
            argumentos_favor=["Pró 1", "Pró 2"],
            argumentos_contra=["Contra 1", "Contra 2"],
            provedor_llm="google",
            modelo="gemini-2.5-flash",
        )

        v2 = await analise_service.create_analysis(create_data_v2)
        assert v2.versao == 2

        # Latest should be v2
        latest = await analise_service.get_latest(proposicao.id)
        assert latest.versao == 2
        assert latest.resumo_leigo == "Versão 2 — atualizada"


# ---------------------------------------------------------------------------
# Admin endpoint tests
# ---------------------------------------------------------------------------


class TestAdminAnaliseEndpoints:
    """Tests for the admin /analise endpoints."""

    @pytest.fixture
    async def proposicao(self, db_session, sample_proposicao_data):
        prop = Proposicao(**sample_proposicao_data)
        db_session.add(prop)
        await db_session.flush()
        await db_session.refresh(prop)
        return prop

    @pytest.fixture
    async def existing_analysis(self, db_session, proposicao):
        """Create an existing analysis in the DB."""
        service = AnaliseIAService(db_session)
        return await service.create_analysis(AnaliseIACreate(
            proposicao_id=proposicao.id,
            resumo_leigo="Análise existente",
            impacto_esperado="Impacto existente",
            areas_afetadas=["Saúde"],
            argumentos_favor=["Pró"],
            argumentos_contra=["Contra"],
            provedor_llm="google",
            modelo="gemini-2.0-flash",
        ))

    async def test_trigger_analise_queues_task(self, client, proposicao):
        """POST /admin/proposicoes/{id}/analisar queues a Celery task."""
        with patch("app.tasks.generate_analysis.generate_analysis_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                f"/admin/proposicoes/{proposicao.id}/analisar",
                headers={"X-API-Key": "change-me-random-64-chars"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["proposicao_id"] == proposicao.id

    async def test_trigger_analise_404_for_missing(self, client):
        """POST /admin/proposicoes/99999/analisar returns 404."""
        with patch("app.tasks.generate_analysis.generate_analysis_task"):
            resp = await client.post(
                "/admin/proposicoes/99999/analisar",
                headers={"X-API-Key": "change-me-random-64-chars"},
            )
        assert resp.status_code == 404

    async def test_get_analise_returns_latest(self, client, existing_analysis):
        """GET /admin/proposicoes/{id}/analise returns latest analysis."""
        resp = await client.get(
            f"/admin/proposicoes/{existing_analysis.proposicao_id}/analise",
            headers={"X-API-Key": "change-me-random-64-chars"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["analise"]["resumo_leigo"] == "Análise existente"

    async def test_get_analise_404_when_none(self, client, proposicao):
        """GET /admin/proposicoes/{id}/analise returns 404 when no analysis."""
        resp = await client.get(
            f"/admin/proposicoes/{proposicao.id}/analise",
            headers={"X-API-Key": "change-me-random-64-chars"},
        )
        assert resp.status_code == 404

    async def test_trigger_reanalyze_all(self, client):
        """POST /admin/analises/reanalyze queues the reanalyze task."""
        with patch("app.tasks.generate_analysis.reanalyze_all_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                "/admin/analises/reanalyze",
                headers={"X-API-Key": "change-me-random-64-chars"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"
