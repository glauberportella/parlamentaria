"""Celery async tasks package."""

from app.tasks.celery_app import celery_app  # noqa: F401
from app.tasks.sync_proposicoes import sync_proposicoes_task  # noqa: F401
from app.tasks.sync_votacoes import sync_votacoes_task  # noqa: F401
from app.tasks.sync_deputados import sync_deputados_task  # noqa: F401
from app.tasks.sync_partidos import sync_partidos_task  # noqa: F401
from app.tasks.sync_eventos import sync_eventos_task  # noqa: F401
from app.tasks.gerar_comparativos import gerar_comparativos_task  # noqa: F401
from app.tasks.generate_embeddings import (  # noqa: F401
    generate_embeddings_task,
    reindex_all_embeddings_task,
)
from app.tasks.generate_analysis import (  # noqa: F401
    generate_analysis_task,
    reanalyze_all_task,
)
from app.tasks.dispatch_webhooks import dispatch_webhooks_task  # noqa: F401
from app.tasks.notificar_eleitores import (  # noqa: F401
    notificar_eleitores_task,
    notificar_comparativo_task,
)
from app.tasks.social_media_tasks import (  # noqa: F401
    post_resumo_semanal_task,
    post_comparativo_task,
    post_votacao_relevante_task,
    post_explicativo_educativo_task,
    post_destaque_proposicao_task,
    atualizar_metricas_task,
    publicar_post_aprovado_task,
)

# Celery CLI expects `app.tasks.celery` or `app.tasks.app` when invoked with -A app.tasks
celery = celery_app
