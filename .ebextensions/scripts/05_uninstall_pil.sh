#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Uninstalling pillow...'
  source /opt/python/run/venv/bin/activate
  yes | pip uninstall Pillow
else
  echo 'The script 05_uninstall_pil.sh is only executed in non-docker environments.'
fi
