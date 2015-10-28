#!/bin/bash -e
apt-get update
apt-get install -qyy -o APT::Install-Recommends=false -o APT::Install-Suggests=false $@
apt-get clean
rm -rf /var/lib/apt/lists/*
