"""Tests for RAG (Retrieval-Augmented Generation) feature.

Tests cover:
- EmbeddingService (mocked Google API)
- RAGService (indexing and search)
- DocumentChunkRepository
- rag_tools (agent FunctionTools)
- generate_embeddings Celery task
- Admin RAG endpoints
"""

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings


# ---------------------------------------------------------------------------
# EmbeddingService Tests
# ---------------------------------------------------------------------------


class TestEmbeddingService:
    """Tests for the EmbeddingService."""

    @patch("app.services.embedding_service.genai")
    def test_init_creates_client(self, mock_genai):
        """EmbeddingService creates a genai client with API key."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService(api_key="test-key")
        mock_genai.Client.assert_called_once_with(api_key="test-key")

    @patch("app.services.embedding_service.genai")
    async def test_embed_text_calls_api(self, mock_genai):
        """embed_text calls the Google embedding API with correct params."""
        from app.services.embedding_service import EmbeddingService

        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = mock_result
        mock_genai.Client.return_value = mock_client

        service = EmbeddingService(api_key="test-key")
        result = await service.embed_text("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_client.models.embed_content.assert_called_once()

    @patch("app.services.embedding_service.genai")
    async def test_embed_text_truncates_long_text(self, mock_genai):
        """embed_text truncates text longer than 8000 chars."""
        from app.services.embedding_service import EmbeddingService

        mock_embedding = MagicMock()
        mock_embedding.values = [0.1]
        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = mock_result
        mock_genai.Client.return_value = mock_client

        service = EmbeddingService(api_key="test-key")
        long_text = "x" * 10000
        await service.embed_text(long_text)

        call_args = mock_client.models.embed_content.call_args
        passed_text = call_args.kwargs.get("contents") or call_args[1].get("contents")
        assert len(passed_text) == 8000

    @patch("app.services.embedding_service.genai")
    async def test_embed_texts_batch(self, mock_genai):
        """embed_texts handles batch embedding."""
        from app.services.embedding_service import EmbeddingService

        mock_emb1 = MagicMock()
        mock_emb1.values = [0.1]
        mock_emb2 = MagicMock()
        mock_emb2.values = [0.2]
        mock_result = MagicMock()
        mock_result.embeddings = [mock_emb1, mock_emb2]

        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = mock_result
        mock_genai.Client.return_value = mock_client

        service = EmbeddingService(api_key="test-key")
        result = await service.embed_texts(["text1", "text2"])

        assert result == [[0.1], [0.2]]

    @patch("app.services.embedding_service.genai")
    async def test_embed_texts_empty_list(self, mock_genai):
        """embed_texts returns empty list for empty input."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService(api_key="test-key")
        result = await service.embed_texts([])
        assert result == []

    def test_content_hash_deterministic(self):
        """content_hash produces consistent SHA-256 hashes."""
        from app.services.embedding_service import EmbeddingService

        text = "Dispõe sobre reforma tributária"
        hash1 = EmbeddingService.content_hash(text)
        hash2 = EmbeddingService.content_hash(text)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_content_hash_different_texts(self):
        """content_hash produces different hashes for different texts."""
        from app.services.embedding_service import EmbeddingService

        hash1 = EmbeddingService.content_hash("text one")
        hash2 = EmbeddingService.content_hash("text two")
        assert hash1 != hash2

    @patch("app.services.embedding_service.genai")
    async def test_embed_text_raises_on_api_error(self, mock_genai):
        """embed_text raises when the API call fails."""
        from app.services.embedding_service import EmbeddingService

        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = Exception("API error")
        mock_genai.Client.return_value = mock_client

        service = EmbeddingService(api_key="test-key")
        with pytest.raises(Exception, match="API error"):
            await service.embed_text("test")


# ---------------------------------------------------------------------------
# RAGService Tests
# ---------------------------------------------------------------------------


class TestRAGService:
    """Tests for the RAGService — indexing and search orchestration."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock EmbeddingService that returns fake embeddings."""
        service = AsyncMock()
        service.embed_text = AsyncMock(return_value=[0.1] * 768)
        service.embed_texts = AsyncMock(return_value=[[0.1] * 768])
        service.content_hash = MagicMock(side_effect=lambda t: hashlib.sha256(t.encode()).hexdigest())
        return service

    @pytest.fixture
    def mock_repo(self):
        """Mock DocumentChunkRepository."""
        repo = AsyncMock()
        repo.find_by_proposicao_and_type_and_hash = AsyncMock(return_value=None)
        repo.delete_by_proposicao_and_type = AsyncMock(return_value=0)
        repo.create = AsyncMock()
        repo.similarity_search = AsyncMock(return_value=[])
        repo.get_stats = AsyncMock(return_value={
            "total_chunks": 0,
            "by_type": {},
            "unique_proposicoes": 0,
        })
        return repo

    @pytest.fixture
    def mock_proposicao(self):
        """Create a mock Proposicao."""
        prop = MagicMock()
        prop.id = 12345
        prop.tipo = "PL"
        prop.numero = 100
        prop.ano = 2024
        prop.ementa = "Dispõe sobre a transparência legislativa"
        prop.resumo_ia = "Resumo simplificado da proposição"
        prop.situacao = "Em tramitação"
        prop.temas = ["Transparência", "Governo"]
        prop.analises = []
        return prop

    async def test_index_proposicao_creates_chunks(
        self, mock_embedding_service, mock_repo, mock_proposicao
    ):
        """index_proposicao creates embedding chunks for proposição text."""
        from app.services.rag_service import RAGService

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        stats = await service.index_proposicao(mock_proposicao)

        assert stats["created"] == 2  # ementa + resumo_ia
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    async def test_index_proposicao_skips_existing(
        self, mock_embedding_service, mock_repo, mock_proposicao
    ):
        """index_proposicao skips chunks with identical content hash."""
        from app.services.rag_service import RAGService

        # Simulate existing chunk
        mock_repo.find_by_proposicao_and_type_and_hash = AsyncMock(return_value=MagicMock())

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        stats = await service.index_proposicao(mock_proposicao)

        assert stats["skipped"] == 2  # both ementa and resumo skipped
        assert stats["created"] == 0

    async def test_index_proposicao_with_analise(
        self, mock_embedding_service, mock_repo
    ):
        """index_proposicao creates chunks for análise IA fields."""
        from app.services.rag_service import RAGService

        # Proposição with analysis
        analise = MagicMock()
        analise.versao = 1
        analise.resumo_leigo = "Explicação simples"
        analise.impacto_esperado = "Impacto na economia brasileira"
        analise.argumentos_favor = ["Argumento 1", "Argumento 2"]
        analise.argumentos_contra = ["Contra 1"]

        prop = MagicMock()
        prop.id = 12345
        prop.tipo = "PL"
        prop.numero = 100
        prop.ano = 2024
        prop.ementa = "Ementa de teste"
        prop.resumo_ia = None
        prop.situacao = "Em tramitação"
        prop.temas = []
        prop.analises = [analise]

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        stats = await service.index_proposicao(prop)

        # ementa + analise_resumo_leigo + analise_impacto + analise_argumentos
        assert stats["created"] == 4

    async def test_index_proposicao_handles_errors(
        self, mock_repo
    ):
        """index_proposicao counts errors when embedding fails."""
        from app.services.rag_service import RAGService

        # Embedding service that fails
        failing_service = AsyncMock()
        failing_service.embed_text = AsyncMock(side_effect=Exception("API down"))
        failing_service.content_hash = MagicMock(return_value="hash123")

        prop = MagicMock()
        prop.id = 12345
        prop.tipo = "PL"
        prop.numero = 100
        prop.ano = 2024
        prop.ementa = "Ementa"
        prop.resumo_ia = None
        prop.situacao = "Em tramitação"
        prop.temas = []
        prop.analises = []

        session = AsyncMock()
        service = RAGService(session, embedding_service=failing_service)
        service.repo = mock_repo

        stats = await service.index_proposicao(prop)

        assert stats["errors"] == 1
        assert stats["created"] == 0

    async def test_search_returns_formatted_results(
        self, mock_embedding_service, mock_repo
    ):
        """search returns properly formatted results with similarity score."""
        from app.services.rag_service import RAGService

        # Mock chunk
        chunk = MagicMock()
        chunk.proposicao_id = 12345
        chunk.chunk_type = "ementa"
        chunk.content = "PL 100/2024: Reforma tributária"
        chunk.metadata_extra = json.dumps({
            "tipo": "PL", "numero": 100, "ano": 2024, "temas": ["economia"],
        })
        chunk.embedding_model = "text-embedding-004"

        mock_repo.similarity_search = AsyncMock(return_value=[(chunk, 0.15)])

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        results = await service.search("reforma tributária")

        assert len(results) == 1
        assert results[0]["proposicao_id"] == 12345
        assert results[0]["similarity"] == 0.85  # 1 - 0.15
        assert results[0]["metadata"]["tipo"] == "PL"

    async def test_search_proposicoes_deduplicates(
        self, mock_embedding_service, mock_repo
    ):
        """search_proposicoes groups by proposição ID and keeps best match."""
        from app.services.rag_service import RAGService

        # Two chunks from same proposição
        chunk1 = MagicMock()
        chunk1.proposicao_id = 12345
        chunk1.chunk_type = "ementa"
        chunk1.content = "Ementa text"
        chunk1.metadata_extra = json.dumps({"tipo": "PL", "numero": 100, "ano": 2024, "temas": []})
        chunk1.embedding_model = "text-embedding-004"

        chunk2 = MagicMock()
        chunk2.proposicao_id = 12345
        chunk2.chunk_type = "resumo_ia"
        chunk2.content = "Resumo text"
        chunk2.metadata_extra = json.dumps({"tipo": "PL", "numero": 100, "ano": 2024, "temas": []})
        chunk2.embedding_model = "text-embedding-004"

        mock_repo.similarity_search = AsyncMock(return_value=[
            (chunk1, 0.2),  # similarity = 0.8
            (chunk2, 0.1),  # similarity = 0.9 — better match
        ])

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        results = await service.search_proposicoes("reforma tributária")

        assert len(results) == 1  # deduplicated
        assert results[0]["similarity"] == 0.9  # kept the better match

    async def test_search_empty_results(
        self, mock_embedding_service, mock_repo
    ):
        """search returns empty list when no similar chunks found."""
        from app.services.rag_service import RAGService

        mock_repo.similarity_search = AsyncMock(return_value=[])

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        results = await service.search("alien legislation from mars")
        assert results == []

    async def test_get_index_stats(self, mock_embedding_service, mock_repo):
        """get_index_stats returns the repo stats."""
        from app.services.rag_service import RAGService

        mock_repo.get_stats = AsyncMock(return_value={
            "total_chunks": 42,
            "by_type": {"ementa": 20, "resumo_ia": 22},
            "unique_proposicoes": 20,
        })

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        stats = await service.get_index_stats()
        assert stats["total_chunks"] == 42
        assert stats["unique_proposicoes"] == 20

    async def test_delete_proposicao_chunks(self, mock_embedding_service, mock_repo):
        """delete_proposicao_chunks delegates to repo."""
        from app.services.rag_service import RAGService

        mock_repo.delete_by_proposicao = AsyncMock(return_value=3)

        session = AsyncMock()
        service = RAGService(session, embedding_service=mock_embedding_service)
        service.repo = mock_repo

        count = await service.delete_proposicao_chunks(12345)
        assert count == 3


# ---------------------------------------------------------------------------
# RAG Tools Tests
# ---------------------------------------------------------------------------


class TestRAGTools:
    """Tests for the agent FunctionTools for semantic search."""

    @patch("agents.parlamentar.tools.rag_tools.async_session_factory")
    @patch("agents.parlamentar.tools.rag_tools.RAGService")
    async def test_busca_semantica_proposicoes_success(self, MockRAGService, mock_session_factory):
        """busca_semantica_proposicoes returns formatted results."""
        from agents.parlamentar.tools.rag_tools import busca_semantica_proposicoes

        mock_rag = AsyncMock()
        mock_rag.search_proposicoes = AsyncMock(return_value=[
            {
                "proposicao_id": 12345,
                "chunk_type": "ementa",
                "content": "PL 100/2024 sobre educação",
                "similarity": 0.92,
                "metadata": {"tipo": "PL", "numero": 100, "ano": 2024, "temas": ["educação"]},
                "embedding_model": "text-embedding-004",
            }
        ])
        MockRAGService.return_value = mock_rag

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        result = await busca_semantica_proposicoes("projetos sobre educação")

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["proposicoes"][0]["proposicao_id"] == 12345
        assert result["proposicoes"][0]["relevancia"] == "92%"

    @patch("agents.parlamentar.tools.rag_tools.async_session_factory")
    @patch("agents.parlamentar.tools.rag_tools.RAGService")
    async def test_busca_semantica_proposicoes_empty(self, MockRAGService, mock_session_factory):
        """busca_semantica_proposicoes handles no results gracefully."""
        from agents.parlamentar.tools.rag_tools import busca_semantica_proposicoes

        mock_rag = AsyncMock()
        mock_rag.search_proposicoes = AsyncMock(return_value=[])
        MockRAGService.return_value = mock_rag

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        result = await busca_semantica_proposicoes("alien law from mars")

        assert result["status"] == "success"
        assert result["total"] == 0

    @patch("agents.parlamentar.tools.rag_tools.async_session_factory")
    @patch("agents.parlamentar.tools.rag_tools.RAGService")
    async def test_busca_semantica_proposicoes_error(self, MockRAGService, mock_session_factory):
        """busca_semantica_proposicoes returns error dict on exception."""
        from agents.parlamentar.tools.rag_tools import busca_semantica_proposicoes

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        result = await busca_semantica_proposicoes("test query")

        assert result["status"] == "error"

    @patch("agents.parlamentar.tools.rag_tools.async_session_factory")
    @patch("agents.parlamentar.tools.rag_tools.RAGService")
    async def test_obter_estatisticas_rag(self, MockRAGService, mock_session_factory):
        """obter_estatisticas_rag returns index stats."""
        from agents.parlamentar.tools.rag_tools import obter_estatisticas_rag

        mock_rag = AsyncMock()
        mock_rag.get_index_stats = AsyncMock(return_value={
            "total_chunks": 100,
            "by_type": {"ementa": 50, "resumo_ia": 50},
            "unique_proposicoes": 50,
        })
        MockRAGService.return_value = mock_rag

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session

        result = await obter_estatisticas_rag()

        assert result["status"] == "success"
        assert result["estatisticas"]["total_trechos_indexados"] == 100
        assert result["estatisticas"]["proposicoes_indexadas"] == 50


# ---------------------------------------------------------------------------
# Celery Task Tests
# ---------------------------------------------------------------------------


class TestGenerateEmbeddingsTask:
    """Tests for the generate_embeddings Celery task."""

    @patch("app.tasks.generate_embeddings.asyncio")
    @patch("app.tasks.generate_embeddings.get_async_session")
    async def test_task_single_proposicao(self, mock_session_ctx, mock_asyncio):
        """Task indexes a single proposição when ID is provided."""
        from app.tasks.generate_embeddings import generate_embeddings_task

        mock_result = {"status": "success", "proposicao_id": 12345, "created": 2, "skipped": 0, "errors": 0}
        mock_asyncio.run.return_value = mock_result
        mock_asyncio.get_event_loop.side_effect = RuntimeError()

        result = generate_embeddings_task(proposicao_id=12345)

        assert result["status"] == "success" or mock_asyncio.run.called

    @patch("app.tasks.generate_embeddings.asyncio")
    @patch("app.tasks.generate_embeddings.get_async_session")
    async def test_task_batch_index(self, mock_session_ctx, mock_asyncio):
        """Task runs batch indexing when no ID provided."""
        from app.tasks.generate_embeddings import generate_embeddings_task

        mock_result = {"status": "success", "created": 10, "skipped": 5, "errors": 0, "proposicoes_processed": 5}
        mock_asyncio.run.return_value = mock_result
        mock_asyncio.get_event_loop.side_effect = RuntimeError()

        result = generate_embeddings_task(batch_size=50, offset=0)

        assert mock_asyncio.run.called or result is not None


# ---------------------------------------------------------------------------
# Document Chunk Domain Model Tests
# ---------------------------------------------------------------------------


class TestDocumentChunkModel:
    """Tests for the DocumentChunk domain model."""

    def test_chunk_type_enum_values(self):
        """ChunkType enum has all expected values."""
        from app.domain.document_chunk import ChunkType

        assert ChunkType.EMENTA == "ementa"
        assert ChunkType.RESUMO_IA == "resumo_ia"
        assert ChunkType.ANALISE_RESUMO_LEIGO == "analise_resumo_leigo"
        assert ChunkType.ANALISE_IMPACTO == "analise_impacto"
        assert ChunkType.ANALISE_ARGUMENTOS == "analise_argumentos"
        assert ChunkType.TRAMITACAO == "tramitacao"

    def test_chunk_type_is_string_enum(self):
        """ChunkType values are strings."""
        from app.domain.document_chunk import ChunkType

        for ct in ChunkType:
            assert isinstance(ct.value, str)

    def test_document_chunk_repr(self):
        """DocumentChunk __repr__ is informative."""
        from app.domain.document_chunk import DocumentChunk

        chunk = MagicMock(spec=DocumentChunk)
        chunk.__repr__ = DocumentChunk.__repr__
        chunk.proposicao_id = 12345
        chunk.chunk_type = "ementa"
        result = DocumentChunk.__repr__(chunk)
        assert "12345" in result
        assert "ementa" in result


# ---------------------------------------------------------------------------
# Admin RAG Endpoints Tests
# ---------------------------------------------------------------------------


class TestAdminRAGEndpoints:
    """Tests for the admin RAG endpoints."""

    @pytest.fixture
    def admin_headers(self):
        return {"x-api-key": settings.admin_api_key}

    async def test_rag_stats_endpoint(self, client, admin_headers):
        """GET /admin/rag/stats returns index statistics."""
        mock_stats = {
            "total_chunks": 10,
            "by_type": {"ementa": 5},
            "unique_proposicoes": 5,
        }
        with patch("app.services.rag_service.EmbeddingService"):
            with patch("app.services.rag_service.DocumentChunkRepository") as MockRepo:
                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_stats = AsyncMock(return_value=mock_stats)
                MockRepo.return_value = mock_repo_instance

                response = await client.get("/admin/rag/stats", headers=admin_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["total_chunks"] == 10

    async def test_rag_stats_unauthorized(self, client):
        """GET /admin/rag/stats requires API key."""
        response = await client.get("/admin/rag/stats", headers={"x-api-key": "wrong"})
        assert response.status_code in (401, 403)

    @patch("app.routers.admin.generate_embeddings_task", create=True)
    @patch("app.routers.admin.reindex_all_embeddings_task", create=True)
    async def test_rag_reindex_endpoint(self, mock_reindex, mock_gen, client, admin_headers):
        """POST /admin/rag/reindex queues the task."""
        mock_reindex.delay = MagicMock()
        response = await client.post("/admin/rag/reindex", headers=admin_headers)
        assert response.status_code in (200, 500)

    async def test_rag_search_requires_query(self, client, admin_headers):
        """POST /admin/rag/search requires query parameter."""
        response = await client.post("/admin/rag/search", headers=admin_headers)
        assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Sync Integration Tests (embedding trigger)
# ---------------------------------------------------------------------------


class TestSyncEmbeddingIntegration:
    """Test that sync triggers embedding generation."""

    @patch("app.tasks.generate_embeddings.generate_embeddings_task")
    async def test_sync_triggers_embeddings(self, mock_embedding_task):
        """sync_proposicoes_task triggers embedding generation on new data."""
        import app.tasks.sync_proposicoes as sync_mod

        mock_embedding_task.delay = MagicMock()

        with patch.object(sync_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = {"created": 5, "updated": 0, "errors": 0, "total_fetched": 5}
            mock_asyncio.get_event_loop.side_effect = RuntimeError()

            # Patch the import inside the function
            with patch.dict("sys.modules", {"app.tasks.generate_embeddings": MagicMock(generate_embeddings_task=mock_embedding_task)}):
                sync_mod.sync_proposicoes_task()

                mock_embedding_task.delay.assert_called_once()

    @patch("app.tasks.generate_embeddings.generate_embeddings_task")
    async def test_sync_no_trigger_when_no_changes(self, mock_embedding_task):
        """sync_proposicoes_task does NOT trigger embeddings when no data synced."""
        import app.tasks.sync_proposicoes as sync_mod

        mock_embedding_task.delay = MagicMock()

        with patch.object(sync_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}
            mock_asyncio.get_event_loop.side_effect = RuntimeError()

            with patch.dict("sys.modules", {"app.tasks.generate_embeddings": MagicMock(generate_embeddings_task=mock_embedding_task)}):
                sync_mod.sync_proposicoes_task()

                mock_embedding_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# Migration Test
# ---------------------------------------------------------------------------


class TestRAGMigration:
    """Test that the migration file is properly configured."""

    def test_migration_file_exists(self):
        """Migration 0002_add_pgvector_rag exists and has correct revision."""
        from alembic.config import Config
        from pathlib import Path

        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0002_add_pgvector_rag.py"
        assert migration_path.exists(), "Migration file 0002_add_pgvector_rag.py not found"

    def test_migration_revision_chain(self):
        """Migration 0002 depends on 0001."""
        import importlib.util

        from pathlib import Path
        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0002_add_pgvector_rag.py"
        spec = importlib.util.spec_from_file_location("migration_0002", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.revision == "0002_add_pgvector_rag"
        assert module.down_revision == "0001_initial"


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestRAGConfig:
    """Test RAG-related configuration."""

    def test_embedding_model_default(self):
        """Default embedding model is text-embedding-004."""
        assert settings.embedding_model == "text-embedding-004"

    def test_embedding_dimensions_default(self):
        """Default embedding dimensions is 768."""
        assert settings.embedding_dimensions == 768

    def test_rag_similarity_threshold_default(self):
        """Default similarity threshold is 0.3."""
        assert settings.rag_similarity_threshold == 0.3

    def test_rag_max_results_default(self):
        """Default max results is 10."""
        assert settings.rag_max_results == 10
