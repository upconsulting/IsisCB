#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Collecting statics...'
  source /opt/python/run/venv/bin/activate
  cd isiscb
  python manage.py collectstatic --noinput
else
  echo 'The script 02_collectstatic.sh is only executed in non-docker environments.'
fi
