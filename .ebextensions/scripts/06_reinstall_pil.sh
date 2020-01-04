#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Reinstalling pillow version 6.2.1...'
  source /opt/python/run/venv/bin/activate
  yes | pip install Pillow==6.2.1 --no-cache-dir
else
  echo 'The script 06_reinstall_pil.sh is only executed in non-docker environments.'
fi
