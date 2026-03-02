"""Celery async tasks package."""

from app.tasks.celery_app import celery_app  # noqa: F401

# Celery CLI expects `app.tasks.celery` or `app.tasks.app` when invoked with -A app.tasks
celery = celery_app
