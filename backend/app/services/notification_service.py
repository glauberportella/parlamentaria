"""Service for proactive voter notifications.

Handles sending notifications to voters about new propositions,
voting results, and comparativos via their registered messaging channel.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.eleitor import Eleitor, FrequenciaNotificacao
from app.domain.proposicao import Proposicao
from app.logging import get_logger
from app.repositories.eleitor import EleitorRepository

logger = get_logger(__name__)

# Maximum notifications per day per voter
MAX_DAILY_NOTIFICATIONS = 5


class NotificationService:
    """Orchestrates proactive notifications to voters.

    Sends notification messages via the appropriate channel adapter.
    The actual sending is abstracted through a callable sender function,
    keeping the service channel-agnostic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EleitorRepository(session)

    async def find_voters_by_tema(
        self, tema: str, limit: int = 100
    ) -> Sequence[Eleitor]:
        """Find voters interested in a specific theme.

        Args:
            tema: Theme name.
            limit: Maximum voters to return.

        Returns:
            Sequence of voters interested in the theme.
        """
        return await self.repo.find_by_tema_interesse(tema, limit=limit)

    async def find_voters_for_proposicao(
        self, temas: list[str], limit: int = 500
    ) -> list[Eleitor]:
        """Find unique voters interested in any of the given themes.

        Args:
            temas: List of themes from a proposition.
            limit: Maximum total voters to return.

        Returns:
            Deduplicated list of voters.
        """
        seen_ids: set[uuid.UUID] = set()
        result: list[Eleitor] = []

        for tema in temas:
            voters = await self.repo.find_by_tema_interesse(tema, limit=limit)
            for voter in voters:
                if voter.id not in seen_ids and len(result) < limit:
                    seen_ids.add(voter.id)
                    result.append(voter)

        return result

    def format_nova_proposicao_message(
        self,
        proposicao_id: int,
        tipo: str,
        numero: int,
        ano: int,
        ementa: str,
        temas: list[str],
    ) -> str:
        """Format a notification message for a new proposition.

        Args:
            proposicao_id: Proposition ID.
            tipo: Type (PL, PEC, etc.).
            numero: Number.
            ano: Year.
            ementa: Summary text.
            temas: Related themes.

        Returns:
            Formatted notification text.
        """
        temas_str = ", ".join(temas) if temas else "Sem tema definido"
        return (
            f"📜 <b>Nova Proposição!</b>\n\n"
            f"<b>{tipo} {numero}/{ano}</b>\n"
            f"{ementa}\n\n"
            f"📌 Temas: {temas_str}\n\n"
            f"Quer saber mais? Me pergunte sobre a proposição {proposicao_id} "
            f"ou vote agora mesmo!"
        )

    def format_resultado_votacao_message(
        self,
        proposicao_id: int,
        tipo: str,
        numero: int,
        ano: int,
        total_votos: int,
        percentual_sim: float,
        percentual_nao: float,
        percentual_abstencao: float,
    ) -> str:
        """Format a notification message for a voting result.

        Args:
            proposicao_id: Proposition ID.
            tipo: Type (PL, PEC, etc.).
            numero: Number.
            ano: Year.
            total_votos: Total votes cast.
            percentual_sim: Percentage SIM.
            percentual_nao: Percentage NAO.
            percentual_abstencao: Percentage abstention.

        Returns:
            Formatted notification text.
        """
        return (
            f"📊 <b>Resultado da Votação Popular</b>\n\n"
            f"<b>{tipo} {numero}/{ano}</b>\n\n"
            f"✅ SIM: {percentual_sim:.1f}%\n"
            f"❌ NÃO: {percentual_nao:.1f}%\n"
            f"⚪ Abstenção: {percentual_abstencao:.1f}%\n\n"
            f"Total de votos: {total_votos}\n\n"
            f"Quer mais detalhes? Pergunte-me sobre a proposição {proposicao_id}."
        )

    def format_comparativo_message(
        self,
        proposicao_id: int,
        tipo: str,
        numero: int,
        ano: int,
        resultado_camara: str,
        percentual_sim_popular: float,
        alinhamento: float,
    ) -> str:
        """Format a notification message for a vote comparison.

        Args:
            proposicao_id: Proposition ID.
            tipo: Type (PL, PEC, etc.).
            numero: Number.
            ano: Year.
            resultado_camara: "APROVADO" or "REJEITADO".
            percentual_sim_popular: Popular SIM percentage.
            alinhamento: Alignment score (0.0 to 1.0).

        Returns:
            Formatted notification text.
        """
        resultado_emoji = "✅" if resultado_camara == "APROVADO" else "❌"
        alinhamento_pct = alinhamento * 100

        return (
            f"🏛️ <b>Comparativo: Voto Popular vs Câmara</b>\n\n"
            f"<b>{tipo} {numero}/{ano}</b>\n\n"
            f"{resultado_emoji} Câmara: {resultado_camara}\n"
            f"👥 Voto popular: {percentual_sim_popular:.1f}% SIM\n"
            f"📏 Alinhamento: {alinhamento_pct:.0f}%\n\n"
            f"Quer saber mais? Pergunte-me sobre a proposição {proposicao_id}."
        )

    async def notify_voters_about_proposicao(
        self,
        proposicao_id: int,
        tipo: str,
        numero: int,
        ano: int,
        ementa: str,
        temas: list[str],
        send_fn: Any | None = None,
    ) -> dict:
        """Send notifications to voters interested in a new proposition.

        Args:
            proposicao_id: Proposition ID.
            tipo: Type (PL, PEC, etc.).
            numero: Number.
            ano: Year.
            ementa: Summary text.
            temas: Related themes.
            send_fn: Async callable(chat_id: str, text: str) -> None.
                     If None, notifications are only logged (dry run).

        Returns:
            Dict with notification stats.
        """
        stats = {"total_voters": 0, "sent": 0, "errors": 0, "skipped": 0}

        if not temas:
            logger.info("notification.skip_no_temas", proposicao_id=proposicao_id)
            return stats

        voters = await self.find_voters_for_proposicao(temas)
        stats["total_voters"] = len(voters)

        message = self.format_nova_proposicao_message(
            proposicao_id=proposicao_id,
            tipo=tipo,
            numero=numero,
            ano=ano,
            ementa=ementa,
            temas=temas,
        )

        for voter in voters:
            if not voter.chat_id:
                stats["skipped"] += 1
                continue

            # Only send immediate alerts to voters who opted in (IMEDIATA).
            # Voters on DIARIA/SEMANAL will get these in their digest instead.
            if voter.frequencia_notificacao not in (
                FrequenciaNotificacao.IMEDIATA,
                # Also send to NAO_VERIFICADO voters who haven't set preference
                # (their default is SEMANAL, but they might not know about digests yet)
            ):
                stats["skipped"] += 1
                continue

            if send_fn is not None:
                try:
                    await send_fn(voter.chat_id, message)
                    stats["sent"] += 1
                    logger.info(
                        "notification.sent",
                        chat_id=voter.chat_id,
                        proposicao_id=proposicao_id,
                    )
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        "notification.send_error",
                        chat_id=voter.chat_id,
                        proposicao_id=proposicao_id,
                        error=str(e),
                    )
            else:
                # Dry run — just log
                stats["sent"] += 1
                logger.info(
                    "notification.dry_run",
                    chat_id=voter.chat_id,
                    proposicao_id=proposicao_id,
                )

        logger.info(
            "notification.proposicao.complete",
            proposicao_id=proposicao_id,
            **stats,
        )
        return stats

    async def notify_voters_comparativo(
        self,
        proposicao_id: int,
        tipo: str,
        numero: int,
        ano: int,
        resultado_camara: str,
        percentual_sim_popular: float,
        alinhamento: float,
        send_fn: Any | None = None,
    ) -> dict:
        """Notify voters who voted on a proposition about the comparison result.

        Args:
            proposicao_id: Proposition ID.
            tipo: Type (PL, PEC, etc.).
            numero: Number.
            ano: Year.
            resultado_camara: "APROVADO" or "REJEITADO".
            percentual_sim_popular: Popular SIM percentage.
            alinhamento: Alignment score (0.0 to 1.0).
            send_fn: Async callable(chat_id: str, text: str) -> None.

        Returns:
            Dict with notification stats.
        """
        from app.repositories.voto_popular import VotoPopularRepository

        stats = {"total_voters": 0, "sent": 0, "errors": 0, "skipped": 0}

        voto_repo = VotoPopularRepository(self.session)
        votos = await voto_repo.list_by_proposicao(proposicao_id)
        stats["total_voters"] = len(votos)

        message = self.format_comparativo_message(
            proposicao_id=proposicao_id,
            tipo=tipo,
            numero=numero,
            ano=ano,
            resultado_camara=resultado_camara,
            percentual_sim_popular=percentual_sim_popular,
            alinhamento=alinhamento,
        )

        # Get unique voter chat_ids
        seen_voter_ids: set[uuid.UUID] = set()
        for voto in votos:
            if voto.eleitor_id in seen_voter_ids:
                continue
            seen_voter_ids.add(voto.eleitor_id)

            # Load voter to get chat_id
            voter = await self.repo.get_by_id(voto.eleitor_id)
            if voter is None or not voter.chat_id:
                stats["skipped"] += 1
                continue

            if send_fn is not None:
                try:
                    await send_fn(voter.chat_id, message)
                    stats["sent"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        "notification.comparativo.send_error",
                        chat_id=voter.chat_id,
                        error=str(e),
                    )
            else:
                stats["sent"] += 1
                logger.info(
                    "notification.comparativo.dry_run",
                    chat_id=voter.chat_id,
                    proposicao_id=proposicao_id,
                )

        logger.info(
            "notification.comparativo.complete",
            proposicao_id=proposicao_id,
            **stats,
        )
        return stats
