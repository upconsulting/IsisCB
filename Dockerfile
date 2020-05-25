FROM python:3.7-buster

ENV DJANGO_SETTINGS_MODULE=isiscb.production_settings

RUN mkdir -p /var/logs/ && touch /var/logs/celery-worker.log

COPY isiscb/ .
WORKDIR isiscb
RUN pip install -r requirements.txt

CMD ["celery", "worker", "-A", "isiscb", "--loglevel=INFO", "-f", "/var/logs/celery-worker.log", "-E", "-P", "solo"]
