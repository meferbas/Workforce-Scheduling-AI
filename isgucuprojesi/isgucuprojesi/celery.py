import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isgucuprojesi.settings')

app = Celery('isgucuprojesi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periyodik görevleri tanımla
app.conf.beat_schedule = {
    'run-optimizations-every-minute': {
        'task': 'cizelgeleme.tasks.run_all_optimizations',
        'schedule': 60.0,  # Her 60 saniyede bir (1 dakika)
    },
} 
