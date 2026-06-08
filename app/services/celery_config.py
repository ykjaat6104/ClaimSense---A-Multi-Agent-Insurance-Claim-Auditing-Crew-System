"""
Celery configuration for asynchronous claim processing.
Enables non-blocking execution of the multi-agent workflow via task queue.
"""

import logging
import os

from celery import Celery
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

# ========== CELERY CONFIGURATION ==========

app = Celery("claimsense")

# Read from environment (set by docker-compose) with localhost fallback
_default_broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
_default_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

app.conf.update(
    broker_url=_default_broker,
    result_backend=_default_backend,
    
    # Task configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution limits
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=3600,  # 1 hour hard limit
    task_max_retries=3,
    task_default_retry_delay=60,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        "app.services.celery_tasks.process_claim_audit": {"queue": "claims"},
        "app.services.celery_tasks.generate_report": {"queue": "reports"},
    },
    
    # Queue configuration
    task_queues=(
        Queue("claims", Exchange("claims"), routing_key="claims"),
        Queue("reports", Exchange("reports"), routing_key="reports"),
        Queue("default", Exchange("default"), routing_key="default"),
    ),
)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic (scheduled) tasks if needed."""
    pass  # No periodic tasks for now


@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def debug_task(self):
    """Simple debug task to verify Celery setup."""
    logger.info(f"Debug task running: {self.request.id}")
    return {"status": "ok"}
