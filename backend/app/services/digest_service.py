"""Service for generating periodic engagement digests.

Produces personalized weekly and daily digests for voters, combining:
- New propositions matching their interest themes
- Most-voted propositions across the platform (general engagement)
- Recent popular vote results
- Recent comparativos (popular vs. parliamentary)
- Upcoming plenary events

The digest is formatted for Telegram (HTML parse mode) and designed to
maximise engagement without being spammy.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.comparativo import ComparativoVotacao
from app.domain.eleitor import Eleitor, FrequenciaNotificacao
from app.domain.evento import Evento
from app.domain.proposicao import Proposicao
from app.domain.voto_popular import VotoPopular
from app.logging import get_logger
from app.repositories.eleitor import EleitorRepository

logger = get_logger(__name__)

# Limits to keep digests readable
MAX_PROPOSICOES_PER_DIGEST = 5
MAX_DESTAQUES_PER_DIGEST = 3
MAX_COMPARATIVOS_PER_DIGEST = 3
MAX_EVENTOS_PER_DIGEST = 3


class DigestService:
    """Generates and sends periodic digest notifications.

    Each digest is personalised per voter based on their ``temas_interesse``.
    When there is nothing personally relevant, the digest falls back to
    platform-wide highlights so the voter always receives value.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EleitorRepository(session)

    # ------------------------------------------------------------------
    # Voter selection
    # ------------------------------------------------------------------

    async def find_voters_for_digest(
        self,
        frequencia: FrequenciaNotificacao,
        *,
        limit: int = 500,
    ) -> Sequence[Eleitor]:
        """Find voters who should receive a digest now.

        Selects voters whose ``frequencia_notificacao`` matches and whose
        ``ultimo_digest_enviado`` is old enough (or NULL).

        Args:
            frequencia: Target frequency (DIARIA or SEMANAL).
            limit: Max voters per batch.

        Returns:
            Sequence of eligible voters.
        """
        now = datetime.now(timezone.utc)

        if frequencia == FrequenciaNotificacao.DIARIA:
            cutoff = now - timedelta(hours=20)  # buffer, avoids skipping
        elif frequencia == FrequenciaNotificacao.SEMANAL:
            cutoff = now - timedelta(days=6)
        else:
            return []

        # Also include IMEDIATA voters in daily digest
        target_freqs = [frequencia]
        if frequencia == FrequenciaNotificacao.DIARIA:
            target_freqs.append(FrequenciaNotificacao.IMEDIATA)

        stmt = (
            select(Eleitor)
            .where(
                Eleitor.frequencia_notificacao.in_(target_freqs),
                Eleitor.chat_id.isnot(None),
            )
            .where(
                (Eleitor.ultimo_digest_enviado.is_(None))
                | (Eleitor.ultimo_digest_enviado < cutoff)
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # Content gathering
    # ------------------------------------------------------------------

    async def get_new_proposicoes(
        self,
        since: datetime,
        temas: list[str] | None = None,
        limit: int = MAX_PROPOSICOES_PER_DIGEST,
    ) -> Sequence[Proposicao]:
        """Get propositions created/synced since a given date.

        If ``temas`` is provided, filters to those themes. Otherwise
        returns the most recent propositions overall.

        Args:
            since: Cutoff datetime.
            temas: Optional theme filter.
            limit: Max results.

        Returns:
            Sequence of propositions.
        """
        stmt = (
            select(Proposicao)
            .where(Proposicao.created_at >= since)
            .order_by(desc(Proposicao.created_at))
            .limit(limit)
        )
        if temas:
            # Use PostgreSQL ARRAY any() for tema matching.
            # In SQLite (tests), temas column is adapted to JSON — gracefully
            # fall back to no filtering if the operator is unavailable.
            try:
                from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

                col_type = Proposicao.__table__.columns["temas"].type
                if isinstance(col_type, PG_ARRAY):
                    # Build OR condition: any tema in our filter list matches
                    from sqlalchemy import or_

                    tema_conditions = [Proposicao.temas.any(t) for t in temas]
                    stmt = stmt.where(or_(*tema_conditions))
            except Exception:
                pass  # SQLite — skip tema filter, return all recent

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_most_voted_proposicoes(
        self,
        since: datetime,
        limit: int = MAX_DESTAQUES_PER_DIGEST,
    ) -> list[dict[str, Any]]:
        """Get propositions with the most popular votes in the period.

        Returns lightweight dicts to avoid loading heavy relationships.

        Args:
            since: Cutoff datetime.
            limit: Max results.

        Returns:
            List of dicts with proposicao info and vote count.
        """
        stmt = (
            select(
                Proposicao.id,
                Proposicao.tipo,
                Proposicao.numero,
                Proposicao.ano,
                Proposicao.ementa,
                func.count(VotoPopular.id).label("total_votos"),
            )
            .join(VotoPopular, VotoPopular.proposicao_id == Proposicao.id)
            .where(VotoPopular.data_voto >= since)
            .group_by(Proposicao.id)
            .order_by(desc("total_votos"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": r.id,
                "tipo": r.tipo,
                "numero": r.numero,
                "ano": r.ano,
                "ementa": r.ementa[:120],
                "total_votos": r.total_votos,
            }
            for r in rows
        ]

    async def get_recent_comparativos(
        self,
        since: datetime,
        limit: int = MAX_COMPARATIVOS_PER_DIGEST,
    ) -> Sequence[ComparativoVotacao]:
        """Get recent comparison results.

        Args:
            since: Cutoff datetime.
            limit: Max results.

        Returns:
            Sequence of comparativos.
        """
        stmt = (
            select(ComparativoVotacao)
            .where(ComparativoVotacao.data_geracao >= since)
            .order_by(desc(ComparativoVotacao.data_geracao))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_upcoming_eventos(
        self,
        limit: int = MAX_EVENTOS_PER_DIGEST,
    ) -> Sequence[Evento]:
        """Get upcoming plenary events in the next 7 days.

        Args:
            limit: Max results.

        Returns:
            Sequence of upcoming events.
        """
        now = datetime.now(timezone.utc)
        week_ahead = now + timedelta(days=7)

        stmt = (
            select(Evento)
            .where(Evento.data_inicio >= now, Evento.data_inicio <= week_ahead)
            .order_by(Evento.data_inicio)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_platform_stats(self, since: datetime) -> dict[str, int]:
        """Get platform engagement stats for the period.

        Args:
            since: Cutoff datetime.

        Returns:
            Dict with counts of votes, voters, propositions.
        """
        # Total popular votes in period
        votes_stmt = (
            select(func.count(VotoPopular.id))
            .where(VotoPopular.data_voto >= since)
        )
        votes_result = await self.session.execute(votes_stmt)
        total_votes = votes_result.scalar() or 0

        # Distinct voters in period
        voters_stmt = (
            select(func.count(func.distinct(VotoPopular.eleitor_id)))
            .where(VotoPopular.data_voto >= since)
        )
        voters_result = await self.session.execute(voters_stmt)
        active_voters = voters_result.scalar() or 0

        # New propositions in period
        props_stmt = (
            select(func.count(Proposicao.id))
            .where(Proposicao.created_at >= since)
        )
        props_result = await self.session.execute(props_stmt)
        new_props = props_result.scalar() or 0

        return {
            "total_votos": total_votes,
            "eleitores_ativos": active_voters,
            "novas_proposicoes": new_props,
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_digest(
        self,
        voter: Eleitor,
        periodo_label: str,
        proposicoes_relevantes: Sequence[Proposicao],
        destaques: list[dict[str, Any]],
        comparativos: Sequence[ComparativoVotacao],
        eventos: Sequence[Evento],
        stats: dict[str, int],
    ) -> str:
        """Format a complete digest message for a voter.

        Args:
            voter: The voter receiving the digest.
            periodo_label: Human-readable period ("esta semana", "hoje").
            proposicoes_relevantes: Props matching voter interests.
            destaques: Most-voted propositions platform-wide.
            comparativos: Recent comparison results.
            eventos: Upcoming plenary events.
            stats: Platform stats for the period.

        Returns:
            HTML-formatted digest text for Telegram.
        """
        parts: list[str] = []

        # Header
        nome = voter.nome.split()[0] if voter.nome else "Eleitor"
        parts.append(
            f"📰 <b>Resumo da Câmara — {periodo_label}</b>\n"
            f"Olá, {nome}! Veja o que aconteceu no Legislativo:\n"
        )

        # Section 1: Propositions matching interests
        if proposicoes_relevantes:
            parts.append("📜 <b>Nos seus temas de interesse:</b>")
            for p in proposicoes_relevantes[:MAX_PROPOSICOES_PER_DIGEST]:
                temas_str = ", ".join(p.temas[:3]) if p.temas else ""
                ementa_short = p.ementa[:100] + ("..." if len(p.ementa) > 100 else "")
                parts.append(
                    f"  • <b>{p.tipo} {p.numero}/{p.ano}</b> — {ementa_short}"
                    + (f"\n    📌 {temas_str}" if temas_str else "")
                )
            parts.append("")

        # Section 2: Platform highlights (most voted)
        if destaques:
            parts.append("🔥 <b>Mais votadas pela comunidade:</b>")
            for d in destaques:
                parts.append(
                    f"  • <b>{d['tipo']} {d['numero']}/{d['ano']}</b> "
                    f"— {d['total_votos']} votos"
                    f"\n    {d['ementa']}"
                )
            parts.append("")

        # Section 3: Comparativos
        if comparativos:
            parts.append("🏛️ <b>Voto Popular vs Câmara:</b>")
            for c in comparativos:
                emoji = "✅" if c.resultado_camara == "APROVADO" else "❌"
                alin_pct = c.alinhamento * 100
                parts.append(
                    f"  • Proposição {c.proposicao_id}: "
                    f"Câmara {emoji} {c.resultado_camara} | "
                    f"Alinhamento: {alin_pct:.0f}%"
                )
            parts.append("")

        # Section 4: Upcoming events
        if eventos:
            parts.append("📅 <b>Agenda da Câmara:</b>")
            for ev in eventos:
                data_str = ev.data_inicio.strftime("%d/%m %H:%M")
                desc_short = ev.descricao[:80] + ("..." if len(ev.descricao) > 80 else "")
                parts.append(f"  • {data_str} — {desc_short}")
            parts.append("")

        # Section 5: Stats
        if stats["total_votos"] > 0:
            parts.append(
                f"📊 <b>Números {periodo_label}:</b>\n"
                f"  {stats['total_votos']} votos populares · "
                f"{stats['eleitores_ativos']} eleitores ativos · "
                f"{stats['novas_proposicoes']} novas proposições"
            )
            parts.append("")

        # Footer with CTA
        if not proposicoes_relevantes and not destaques:
            parts.append(
                "💬 Nenhuma novidade relevante no período, mas continue "
                "acompanhando! Pergunte-me sobre qualquer proposição."
            )

        parts.append(
            "💡 <i>Dica: envie \"quero notificações diárias\" ou "
            "\"desativar notificações\" para ajustar a frequência.</i>"
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Digest generation (orchestration)
    # ------------------------------------------------------------------

    async def generate_digest_for_voter(
        self,
        voter: Eleitor,
        periodo_dias: int,
    ) -> str:
        """Generate a complete digest for a single voter.

        Args:
            voter: The voter to generate the digest for.
            periodo_dias: Number of days to look back (1 for daily, 7 for weekly).

        Returns:
            Formatted digest text ready to send.
        """
        since = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
        periodo_label = "esta semana" if periodo_dias >= 7 else "hoje"

        # Gather all content in parallel (sequential here, but fast queries)
        proposicoes_relevantes = await self.get_new_proposicoes(
            since=since,
            temas=voter.temas_interesse,
        )
        destaques = await self.get_most_voted_proposicoes(since=since)
        comparativos = await self.get_recent_comparativos(since=since)
        eventos = await self.get_upcoming_eventos()
        stats = await self.count_platform_stats(since=since)

        return self.format_digest(
            voter=voter,
            periodo_label=periodo_label,
            proposicoes_relevantes=proposicoes_relevantes,
            destaques=destaques,
            comparativos=comparativos,
            eventos=eventos,
            stats=stats,
        )

    async def send_digests(
        self,
        frequencia: FrequenciaNotificacao,
        send_fn: Any | None = None,
        batch_size: int = 50,
    ) -> dict[str, int]:
        """Send digests to all eligible voters for the given frequency.

        Args:
            frequencia: DIARIA or SEMANAL.
            send_fn: Async callable(chat_id: str, text: str) -> None.
                     If None, notifications are logged (dry run).
            batch_size: Number of voters to process per batch.

        Returns:
            Stats dict with sent, errors, skipped counts.
        """
        periodo_dias = 7 if frequencia == FrequenciaNotificacao.SEMANAL else 1

        stats = {"total_voters": 0, "sent": 0, "errors": 0, "skipped": 0}

        voters = await self.find_voters_for_digest(frequencia, limit=batch_size)
        stats["total_voters"] = len(voters)

        logger.info(
            "digest.start",
            frequencia=frequencia.value,
            total_voters=len(voters),
        )

        for voter in voters:
            try:
                digest_text = await self.generate_digest_for_voter(
                    voter=voter,
                    periodo_dias=periodo_dias,
                )

                if send_fn is not None:
                    await send_fn(voter.chat_id, digest_text)

                # Mark digest as sent
                voter.ultimo_digest_enviado = datetime.now(timezone.utc)
                stats["sent"] += 1

                logger.info(
                    "digest.sent",
                    chat_id=voter.chat_id,
                    frequencia=frequencia.value,
                )

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    "digest.send_error",
                    chat_id=voter.chat_id,
                    error=str(e),
                )

        # Commit updated ultimo_digest_enviado timestamps
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.warning("digest.commit_failed_rollback")

        logger.info("digest.complete", frequencia=frequencia.value, **stats)
        return stats

    # ------------------------------------------------------------------
    # Preference management
    # ------------------------------------------------------------------

    async def update_notification_preferences(
        self,
        chat_id: str,
        frequencia: FrequenciaNotificacao,
        horario: int = 9,
    ) -> dict[str, str]:
        """Update notification preferences for a voter.

        Args:
            chat_id: Voter chat ID.
            frequencia: Desired notification frequency.
            horario: Preferred hour (0-23).

        Returns:
            Dict with status and confirmation message.
        """
        voter = await self.repo.find_by_chat_id(chat_id)
        if voter is None:
            return {
                "status": "not_found",
                "message": "Eleitor não cadastrado.",
            }

        voter.frequencia_notificacao = frequencia
        voter.horario_preferido_notificacao = max(0, min(23, horario))
        await self.session.commit()

        freq_labels = {
            FrequenciaNotificacao.IMEDIATA: "imediata (alertas + resumo diário)",
            FrequenciaNotificacao.DIARIA: "diária (resumo todo dia)",
            FrequenciaNotificacao.SEMANAL: "semanal (resumo toda segunda)",
            FrequenciaNotificacao.DESATIVADA: "desativada",
        }

        return {
            "status": "success",
            "message": (
                f"Frequência de notificação alterada para: "
                f"{freq_labels[frequencia]}. "
                f"Horário preferido: {horario}h."
            ),
        }
