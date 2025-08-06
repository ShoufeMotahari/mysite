import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task routing
    task_routes={
        'emails.tasks.send_broadcast_email': {'queue': 'email_queue'},
        'emails.tasks.send_single_email': {'queue': 'email_queue'},
        'emails.tasks.cleanup_old_email_logs': {'queue': 'maintenance_queue'},
    },

    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,

    # Task time limits
    task_soft_time_limit=600,  # 10 minutes
    task_time_limit=900,  # 15 minutes

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
    } if hasattr(settings, 'CELERY_RESULT_BACKEND') and 'redis' in settings.CELERY_RESULT_BACKEND else {},
)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')