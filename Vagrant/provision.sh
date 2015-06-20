#!/bin/bash

set -e

# CONSTANTS

# FUNCTIONS
error() {
    echo "ERROR: $@" >&2
}

install_dependencies() {
    # Installing dependencies
    echo "==============================="
    echo "Installing dependencies"
    sleep 2
    apt-get update &&
    apt-get install -y python-pip python-dev build-essential &&
    apt-get install -y libfreetype6-dev libpng-dev pkg-config &&
    pip install -U ipdb &&
    pip install -r /opt/code/requirements.txt || { error "Something was wrong installing deps" ; exit 1 ; }
    echo "==============================="
}

# MAIN
install_dependencies
