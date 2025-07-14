#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
    port="5001"
else
    port=$1
fi

echo Starting ELCM on port $port
source ./venv/bin/activate
waitress-serve --threads=1 --listen=*:$port Scheduler:app
deactivate
