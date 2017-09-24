#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Updating pip...'
  source /opt/python/run/venv/bin/activate
  pip install -U six==1.10.0
else
  echo 'The script 07_update_pip.sh is only executed in non-docker environments.'
fi
