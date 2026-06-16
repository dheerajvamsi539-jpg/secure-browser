#!/bin/bash
# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Run the application using system python (dependencies are already verified)
python3 "$DIR/main.py" "$@"
