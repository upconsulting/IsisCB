#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Installing pycurl with nss...'
  source /opt/python/run/venv/bin/activate
  PYCURL_SSL_LIBRARY=nss /opt/python/run/venv/bin/pip install --ignore-installed --no-cache-dir --install-option='--with-nss' --compile pycurl
else
  echo 'The script 10_intall_pycurl_with_nss.sh is only executed in non-docker environments.'
fi
