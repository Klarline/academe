"""
Celery configuration for Academe background tasks.

Handles:
- Memory updates
- Progress tracking
- Document processing
- Future: Email notifications, scheduled tasks
"""

from celery import Celery
from celery.signals import worker_ready
from kombu import Exchange, Queue
import os


# Initialize Celery app
celery_app = Celery('academe')

# Configuration
celery_app.conf.update(
    # Broker settings
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Retry settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    
    # Performance
    worker_prefetch_multiplier=4,  # How many tasks to prefetch
    worker_max_tasks_per_child=1000,  # Restart worker after N tasks (prevents memory leaks)
    
    # Task routing (priority queues)
    task_routes={
        'academe.update_memory': {'queue': 'memory'},
        'academe.process_document': {'queue': 'documents'},
        'academe.update_progress': {'queue': 'memory'},
        'academe.index_document': {'queue': 'documents'},
    },
    
    # Queue definitions
    task_queues=(
        Queue('memory', Exchange('memory'), routing_key='memory', priority=5),
        Queue('documents', Exchange('documents'), routing_key='documents', priority=3),
        Queue('default', Exchange('default'), routing_key='default', priority=1),
    ),
    
    # Monitoring
    task_track_started=True,  # Track when task starts
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # Warn at 4 minutes
)

# Task autodiscovery
celery_app.autodiscover_tasks(['core'])


# Initialize database when worker starts
@worker_ready.connect
def init_worker_database(sender=None, **kwargs):
    """Initialize database connection when Celery worker starts."""
    from core.database import init_database
    init_database()
    print("Database initialized for Celery worker")

