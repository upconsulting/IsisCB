#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Pip install...'
  #source /opt/python/run/venv/bin/activate
  source /var/app/venv/staging-LQM1lest/bin/activate
  pip install --use-deprecated=legacy-resolver -r requirements.txt
else
  echo 'The script 01_pip_install.sh is only executed in non-docker environments.'
fi
