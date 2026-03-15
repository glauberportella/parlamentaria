"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "parlamentaria",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.sync_proposicoes",
        "app.tasks.sync_votacoes",
        "app.tasks.sync_deputados",
        "app.tasks.sync_partidos",
        "app.tasks.sync_eventos",
        "app.tasks.notificar_eleitores",
        "app.tasks.dispatch_webhooks",
        "app.tasks.gerar_comparativos",
        "app.tasks.generate_embeddings",
        "app.tasks.generate_analysis",
        "app.tasks.send_digests",
        "app.tasks.social_media_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

# Periodic task schedule (Celery beat)
# Sincronização 2x/dia (manhã 6h e noite 20h) — a Câmara não publica
# proposições/votações com frequência que justifique polling a cada 15 min.
# Tasks escalonadas para que dependências rodem em sequência.
celery_app.conf.beat_schedule = {
    # === Manhã (5h30-7h) ===
    # Partidos e deputados primeiro (dados referenciais)
    "sync-partidos-morning": {
        "task": "app.tasks.sync_partidos.sync_partidos_task",
        "schedule": crontab(hour=5, minute=30),  # 05:30
        "args": (),
    },
    "sync-deputados-morning": {
        "task": "app.tasks.sync_deputados.sync_deputados_task",
        "schedule": crontab(hour=5, minute=45),  # 05:45
        "args": (),
    },
    "sync-proposicoes-morning": {
        "task": "app.tasks.sync_proposicoes.sync_proposicoes_task",
        "schedule": crontab(hour=6, minute=0),  # 06:00
        "args": (),
    },
    "sync-votacoes-morning": {
        "task": "app.tasks.sync_votacoes.sync_votacoes_task",
        "schedule": crontab(hour=6, minute=30),  # 06:30
        "args": (),
    },
    "sync-eventos-morning": {
        "task": "app.tasks.sync_eventos.sync_eventos_task",
        "schedule": crontab(hour=6, minute=45),  # 06:45
        "args": (),
    },
    "gerar-comparativos-morning": {
        "task": "app.tasks.gerar_comparativos.gerar_comparativos_task",
        "schedule": crontab(hour=7, minute=0),  # 07:00
        "args": (),
    },
    # === Noite (19h30-21h) — captura resultados de sessões diurnas ===
    "sync-partidos-evening": {
        "task": "app.tasks.sync_partidos.sync_partidos_task",
        "schedule": crontab(hour=19, minute=30),  # 19:30
        "args": (),
    },
    "sync-deputados-evening": {
        "task": "app.tasks.sync_deputados.sync_deputados_task",
        "schedule": crontab(hour=19, minute=45),  # 19:45
        "args": (),
    },
    "sync-proposicoes-evening": {
        "task": "app.tasks.sync_proposicoes.sync_proposicoes_task",
        "schedule": crontab(hour=20, minute=0),  # 20:00
        "args": (),
    },
    "sync-votacoes-evening": {
        "task": "app.tasks.sync_votacoes.sync_votacoes_task",
        "schedule": crontab(hour=20, minute=30),  # 20:30
        "args": (),
    },
    "sync-eventos-evening": {
        "task": "app.tasks.sync_eventos.sync_eventos_task",
        "schedule": crontab(hour=20, minute=45),  # 20:45
        "args": (),
    },
    "gerar-comparativos-evening": {
        "task": "app.tasks.gerar_comparativos.gerar_comparativos_task",
        "schedule": crontab(hour=21, minute=0),  # 21:00
        "args": (),
    },
    # === Madrugada — manutenção ===
    "reindex-embeddings-daily": {
        "task": "app.tasks.generate_embeddings.reindex_all_embeddings_task",
        "schedule": crontab(hour=3, minute=0),  # 03:00
        "args": (),
    },
    # === Engagement Digests ===
    # Daily digest: sent after morning sync completes (08:30)
    # Targets voters with frequencia_notificacao = DIARIA or IMEDIATA
    "send-daily-digest": {
        "task": "app.tasks.send_digests.send_daily_digest_task",
        "schedule": crontab(
            hour=settings.digest_daily_hour,
            minute=settings.digest_daily_minute,
        ),
        "args": (),
    },
    # Weekly digest: sent every Monday at 09:00
    # Targets voters with frequencia_notificacao = SEMANAL (default)
    "send-weekly-digest": {
        "task": "app.tasks.send_digests.send_weekly_digest_task",
        "schedule": crontab(
            hour=settings.digest_weekly_hour,
            minute=0,
            day_of_week=settings.digest_weekly_day,
        ),
        "args": (),
    },
    # === Social Media ===
    # Weekly summary: posted after weekly digest (default: Mondays at SOCIAL_WEEKLY_HOUR)
    "social-resumo-semanal": {
        "task": "app.tasks.social_media_tasks.post_resumo_semanal_task",
        "schedule": crontab(
            hour=settings.social_weekly_hour,
            minute=0,
            day_of_week=settings.digest_weekly_day,
        ),
        "args": (),
    },
    # Metrics update: 4x/day (every 6 hours)
    "social-atualizar-metricas": {
        "task": "app.tasks.social_media_tasks.atualizar_metricas_task",
        "schedule": crontab(hour="0,6,12,18", minute=15),
        "args": (),
    },
}
