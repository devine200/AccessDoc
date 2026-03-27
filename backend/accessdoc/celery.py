import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accessdoc.settings")

app = Celery("accessdoc")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
