#!/bin/bash

echo 'This is a docker environment: $IS_DOCKER'

if [ "$IS_DOCKER" != "true" ]; then
  echo 'Copying wsgi conf file...'
  cp wsgi.conf ../wsgi.conf
else
  echo 'The script 04_wsgipass.sh is only executed in non-docker environments.'
fi
