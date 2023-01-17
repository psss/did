#!/bin/bash

podman image pull fedora
version=$(podman run -it --rm fedora grep VERSION_ID /etc/os-release | tr -d "\r\n")

export CURRENT_VERSION=${version/*=/}
export PREVIOUS_VERSION=$(($CURRENT_VERSION - 1))
export UPGRADE_PATH="/paths/fedora${PREVIOUS_VERSION}to${CURRENT_VERSION}"

echo "Found fedora version: current=$CURRENT_VERSION, previous=$PREVIOUS_VERSION"
