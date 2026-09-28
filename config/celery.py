import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat fires this on a fixed interval, independent of any player action --
# unlike bot_decide_task, nothing in the WebSocket/consumer layer ever
# triggers it. The task itself (table.tasks.check_turn_timeouts) decides
# what "timed out" means and what to do about it.
app.conf.beat_schedule = {
    'check-turn-timeouts': {
        'task': 'table.tasks.check_turn_timeouts',
        'schedule': 5.0,  # seconds between checks
    },
}
