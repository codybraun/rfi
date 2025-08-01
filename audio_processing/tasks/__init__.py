from celery import Celery

from django.conf import settings

celery = Celery('tasks', broker=settings.CELERY_BROKER_URL)
