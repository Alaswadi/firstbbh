"""
Celery application configuration for bug bounty automation.
"""
from celery import Celery
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_SOFT_TIME_LIMIT, CELERY_TASK_TIME_LIMIT

# Create Celery instance
celery_app = Celery(
    'bbh_automation',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['tasks']  # Import tasks module
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_send_sent_event=True,
    task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=CELERY_TASK_TIME_LIMIT,
    
    # Task result settings
    result_expires=86400,  # Results expire after 24 hours
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    
    # Task routing
    task_routes={
        'tasks.scan_domain_task': {'queue': 'scans'},
        'tasks.run_subdomain_discovery_task': {'queue': 'discovery'},
        'tasks.run_port_scan_task': {'queue': 'scanning'},
        'tasks.run_web_probing_task': {'queue': 'probing'},
    },
    
    # Default queue
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Retry settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
)

# Optional: Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Run a cleanup task daily
    # 'cleanup-old-scans': {
    #     'task': 'tasks.cleanup_old_scans',
    #     'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    # },
}

if __name__ == '__main__':
    celery_app.start()
