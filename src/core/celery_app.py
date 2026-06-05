from celery import Celery

from src.core.config import settings


celery_app = Celery(
    "bim_pipeline",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
    include=["src.tasks.ifc_import_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 60,
    task_soft_time_limit=55 * 60,
)

import src.tasks.ifc_import_tasks  # noqa: E402,F401
