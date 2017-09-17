FROM python:2.7-onbuild

ENV DJANGO_SETTINGS_MODULE=isiscb.production_settings

RUN mkdir -p /var/logs/ && touch /var/logs/celery-worker.log

WORKDIR isiscb
CMD ["celery", "worker", "-A", "isiscb", "--loglevel=INFO", "-f", "/var/logs/celery-worker.log", "-E", "-P", "solo"]
