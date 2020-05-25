FROM python:3.7-buster

ENV DJANGO_SETTINGS_MODULE=isiscb.production_settings

RUN mkdir -p /var/logs/ && touch /var/logs/celery-worker.log

COPY isiscb/ ./isiscb
COPY requirements.txt .
RUN pip install -r requirements.txt

# Docker/AWS requests this although we don't need it?
EXPOSE 80
WORKDIR isiscb
CMD ["celery", "worker", "-A", "isiscb", "--loglevel=INFO", "-f", "/var/logs/celery-worker.log", "-E", "-P", "solo"]
