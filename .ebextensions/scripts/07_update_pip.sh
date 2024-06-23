#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Updating pip...'
  #source /opt/python/run/venv/bin/activate
  source /var/app/venv/staging-LQM1lest/bin/activate
  pip install pip==23.3.2
else
  echo 'The script 07_update_pip.sh is only executed in non-docker environments.'
fi
