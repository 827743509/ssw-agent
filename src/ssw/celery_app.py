"""Celery 应用实例。

启动 worker：`uv run celery -A ssw.celery_app:celery_app worker -l info`
任务定义见 `ssw.ingestion.tasks`，通过 `include` 让 worker 启动时自动发现。
"""

from celery import Celery

from ssw.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "rag_knowledge_base",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["ssw.ingestion.tasks"],
)

# 文档入库状态由 documents.status 跟踪。
celery_app.conf.update(
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    # 默认 task 序列化为 json，避免 pickle 引入额外约束
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
