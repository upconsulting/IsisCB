#!/bin/bash
set -xe

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