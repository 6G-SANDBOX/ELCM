#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
    port="5001"
else
    port=$1
fi

echo Starting ELCM on port $port
source ./venv/bin/activate
flask run --host 0.0.0.0 --port $port
deactivate
