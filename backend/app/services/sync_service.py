"""Service for synchronization with the Câmara dos Deputados API.

Handles periodic sync of propositions, votes, deputies, parties, and events
from the public Dados Abertos API into the local database.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.camara_client import CamaraClient
from app.logging import get_logger
from app.services.deputado_service import DeputadoService
from app.services.evento_service import EventoService
from app.services.partido_service import PartidoService
from app.services.proposicao_service import ProposicaoService
from app.services.votacao_service import VotacaoService

logger = get_logger(__name__)


class SyncService:
    """Synchronizes data from the Câmara API into the local database.

    Designed to be called periodically (e.g., via Celery beat).
    Uses upsert logic to avoid duplicates.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.proposicao_service = ProposicaoService(session)
        self.votacao_service = VotacaoService(session)
        self.deputado_service = DeputadoService(session)
        self.partido_service = PartidoService(session)
        self.evento_service = EventoService(session)

    async def sync_proposicoes(
        self,
        ano: int | None = None,
        sigla_tipo: str | None = None,
        paginas: int = 3,
        itens_por_pagina: int = 50,
    ) -> dict:
        """Sync propositions from the Câmara API.

        Fetches multiple pages and upserts each proposition.

        Args:
            ano: Year filter (defaults to current year).
            sigla_tipo: Type filter (PL, PEC, etc.).
            paginas: Number of pages to fetch.
            itens_por_pagina: Items per page.

        Returns:
            Dict with created, updated, and error counts.
        """
        if ano is None:
            ano = datetime.now(timezone.utc).year

        stats = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        async with CamaraClient() as client:
            for pagina in range(1, paginas + 1):
                try:
                    proposicoes = await client.listar_proposicoes(
                        ano=ano,
                        sigla_tipo=sigla_tipo,
                        pagina=pagina,
                        itens=itens_por_pagina,
                    )
                except Exception as e:
                    logger.error("sync.proposicoes.fetch_error", pagina=pagina, error=str(e))
                    stats["errors"] += 1
                    continue

                if not proposicoes:
                    break

                stats["total_fetched"] += len(proposicoes)

                for prop_api in proposicoes:
                    try:
                        async with self.session.begin_nested():
                            api_data = {
                                "id": prop_api.id,
                                "tipo": prop_api.siglaTipo,
                                "numero": prop_api.numero,
                                "ano": prop_api.ano,
                                "ementa": prop_api.ementa or "",
                                "data_apresentacao": getattr(prop_api, "dataApresentacao", None),
                                "situacao": "Em tramitação",
                            }
                            await self.proposicao_service.upsert_from_api(api_data)
                        # Savepoint released — upsert succeeded
                        stats["created"] += 1
                    except Exception as e:
                        logger.error(
                            "sync.proposicao.upsert_error",
                            id=prop_api.id,
                            error=str(e),
                        )
                        stats["errors"] += 1
                        # Savepoint rolled back automatically — session still usable

        logger.info("sync.proposicoes.complete", **stats)
        return stats

    async def sync_votacoes(self, paginas: int = 2, itens_por_pagina: int = 50) -> dict:
        """Sync recent parliamentary votes from the Câmara API.

        Args:
            paginas: Number of pages to fetch.
            itens_por_pagina: Items per page.

        Returns:
            Dict with sync statistics.
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        async with CamaraClient() as client:
            for pagina in range(1, paginas + 1):
                try:
                    votacoes = await client.listar_votacoes(
                        pagina=pagina,
                        itens=itens_por_pagina,
                    )
                except Exception as e:
                    logger.error("sync.votacoes.fetch_error", pagina=pagina, error=str(e))
                    stats["errors"] += 1
                    continue

                if not votacoes:
                    break

                stats["total_fetched"] += len(votacoes)

                for vot_api in votacoes:
                    try:
                        async with self.session.begin_nested():
                            api_data = {
                                "id": vot_api.id,
                                "data": vot_api.data if hasattr(vot_api, "data") else None,
                                "descricao": vot_api.descricao or "",
                            }
                            await self.votacao_service.upsert_from_api(api_data)
                        stats["created"] += 1
                    except Exception as e:
                        logger.error(
                            "sync.votacao.upsert_error",
                            id=vot_api.id,
                            error=str(e),
                        )
                        stats["errors"] += 1
                        # Savepoint rolled back automatically — session still usable

        logger.info("sync.votacoes.complete", **stats)
        return stats

    async def sync_deputados(
        self,
        sigla_uf: str | None = None,
        sigla_partido: str | None = None,
        paginas: int = 6,
        itens_por_pagina: int = 100,
    ) -> dict:
        """Sync active deputies from the Câmara API.

        Fetches multiple pages and upserts each deputy.

        Args:
            sigla_uf: State filter.
            sigla_partido: Party filter.
            paginas: Number of pages to fetch (513 deputies / 100 per page = ~6).
            itens_por_pagina: Items per page.

        Returns:
            Dict with sync statistics.
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        async with CamaraClient() as client:
            for pagina in range(1, paginas + 1):
                try:
                    deputados = await client.listar_deputados(
                        sigla_uf=sigla_uf,
                        sigla_partido=sigla_partido,
                        pagina=pagina,
                        itens=itens_por_pagina,
                    )
                except Exception as e:
                    logger.error("sync.deputados.fetch_error", pagina=pagina, error=str(e))
                    stats["errors"] += 1
                    continue

                if not deputados:
                    break

                stats["total_fetched"] += len(deputados)

                for dep_api in deputados:
                    try:
                        async with self.session.begin_nested():
                            api_data = {
                                "id": dep_api.id,
                                "nome": dep_api.nome,
                                "sigla_partido": dep_api.siglaPartido,
                                "sigla_uf": dep_api.siglaUf,
                                "foto_url": dep_api.urlFoto,
                                "email": dep_api.email,
                            }
                            await self.deputado_service.upsert_from_api(api_data)
                        stats["created"] += 1
                    except Exception as e:
                        logger.error(
                            "sync.deputado.upsert_error",
                            id=dep_api.id,
                            error=str(e),
                        )
                        stats["errors"] += 1

        logger.info("sync.deputados.complete", **stats)
        return stats

    async def sync_partidos(self) -> dict:
        """Sync political parties from the Câmara API.

        Parties are few (~30), so we fetch all in a single page.

        Returns:
            Dict with sync statistics.
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        async with CamaraClient() as client:
            try:
                partidos = await client.listar_partidos(itens=100)
            except Exception as e:
                logger.error("sync.partidos.fetch_error", error=str(e))
                stats["errors"] += 1
                return stats

            stats["total_fetched"] = len(partidos)

            for part_api in partidos:
                try:
                    async with self.session.begin_nested():
                        api_data = {
                            "id": part_api.id,
                            "sigla": part_api.sigla,
                            "nome": part_api.nome,
                        }
                        await self.partido_service.upsert_from_api(api_data)
                    stats["created"] += 1
                except Exception as e:
                    logger.error(
                        "sync.partido.upsert_error",
                        id=part_api.id,
                        error=str(e),
                    )
                    stats["errors"] += 1

        logger.info("sync.partidos.complete", **stats)
        return stats

    async def sync_eventos(
        self,
        dias_atras: int = 7,
        paginas: int = 3,
        itens_por_pagina: int = 50,
    ) -> dict:
        """Sync recent plenary events from the Câmara API.

        Args:
            dias_atras: How many days back to sync (default 7).
            paginas: Number of pages to fetch.
            itens_por_pagina: Items per page.

        Returns:
            Dict with sync statistics.
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "total_fetched": 0}

        data_inicio = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        data_fim = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with CamaraClient() as client:
            for pagina in range(1, paginas + 1):
                try:
                    eventos = await client.listar_eventos(
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        pagina=pagina,
                        itens=itens_por_pagina,
                    )
                except Exception as e:
                    logger.error("sync.eventos.fetch_error", pagina=pagina, error=str(e))
                    stats["errors"] += 1
                    continue

                if not eventos:
                    break

                stats["total_fetched"] += len(eventos)

                for evt_api in eventos:
                    try:
                        async with self.session.begin_nested():
                            # Parse datetime strings from API to Python datetime objects
                            data_inicio = None
                            if evt_api.dataHoraInicio:
                                try:
                                    data_inicio = datetime.fromisoformat(evt_api.dataHoraInicio)
                                except (ValueError, TypeError):
                                    data_inicio = evt_api.dataHoraInicio

                            data_fim = None
                            if evt_api.dataHoraFim:
                                try:
                                    data_fim = datetime.fromisoformat(evt_api.dataHoraFim)
                                except (ValueError, TypeError):
                                    data_fim = evt_api.dataHoraFim

                            api_data = {
                                "id": evt_api.id,
                                "descricao": evt_api.descricao or "",
                                "tipo_evento": evt_api.descricaoTipo,
                                "data_inicio": data_inicio,
                                "data_fim": data_fim,
                                "situacao": evt_api.situacao,
                            }
                            await self.evento_service.upsert_from_api(api_data)
                        stats["created"] += 1
                    except Exception as e:
                        logger.error(
                            "sync.evento.upsert_error",
                            id=evt_api.id,
                            error=str(e),
                        )
                        stats["errors"] += 1

        logger.info("sync.eventos.complete", **stats)
        return stats
