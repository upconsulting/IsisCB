#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Updating setuptools...'
  source /opt/python/run/venv/bin/activate
  pip install -U setuptools==33.1.1
else
  echo 'The script 09_update_setuptools.sh is only executed in non-docker environments.'
fi
