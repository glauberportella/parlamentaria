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
        "app.tasks.notificar_eleitores",
        "app.tasks.dispatch_webhooks",
        "app.tasks.gerar_comparativos",
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
celery_app.conf.beat_schedule = {
    "sync-proposicoes-every-15min": {
        "task": "app.tasks.sync_proposicoes.sync_proposicoes_task",
        "schedule": crontab(minute="*/15"),
        "args": (),
    },
    "sync-votacoes-every-15min": {
        "task": "app.tasks.sync_votacoes.sync_votacoes_task",
        "schedule": crontab(minute="*/15"),
        "args": (),
    },
    "gerar-comparativos-every-30min": {
        "task": "app.tasks.gerar_comparativos.gerar_comparativos_task",
        "schedule": crontab(minute="*/30"),
        "args": (),
    },
}
