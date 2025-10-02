#!/bin/bash
set -xe

if [ "$IS_DOCKER" != "true" ]; then
    echo ">>> Installing system packages before requirements.txt"

    dnf install -y \
        git \
        freetype-devel \
        libpng-devel \
        zlib-devel \
        libjpeg-turbo-devel \
        openssl-devel \
        libffi-devel

    echo ">>> System packages installed"
else
    echo ">>> Docker environment detected. Won't install dependencies."
fi