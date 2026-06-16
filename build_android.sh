#!/bin/bash

# Secure Browser Android Build Script
# This script automates the installation of Buildozer dependencies and starts the build.

set -e

echo "--- 1. Installing System Dependencies ---"
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev python3-setuptools libtinfo6

echo "--- 2. Installing Buildozer & Cython ---"
pip3 install --user --upgrade buildozer cython virtualenv --break-system-packages

# Ensure local bin is in PATH
export PATH=$PATH:$HOME/.local/bin
export PIP_BREAK_SYSTEM_PACKAGES=1



echo "--- 4. Starting Android Build ---"
echo "This will download several hundred MBs of Android SDK/NDK. It may take 15-30 minutes."
buildozer android debug

echo "--- Build Process Finished ---"
echo "Check the 'bin/' directory for the .apk file."
