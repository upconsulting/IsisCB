#!/bin/sh

python -m pip install -r requirements.txt
cd isiscb
python manage.py migrate

redis-server --daemonize yes
celery -A isiscb worker -l info --detach --logfile=/app/logs/celery.log --pidfile=
python manage.py createcachetable
python manage.py runserver 0.0.0.0:8000 > /app/logs/django.log