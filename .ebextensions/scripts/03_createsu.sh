#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Creating superuser...'
  source /opt/python/run/venv/bin/activate
  cd isiscb
  python manage.py createsu
else
  echo 'The script 03_createsu.sh is only executed in non-docker environments.'
fi
