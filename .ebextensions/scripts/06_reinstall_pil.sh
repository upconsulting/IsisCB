#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Reinstalling pillow...'
  source /opt/python/run/venv/bin/activate
  yes | pip install Pillow --no-cache-dir
else
  echo 'The script 06_reinstall_pil.sh is only executed in non-docker environments.'
fi
