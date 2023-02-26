#!/bin/bash

export $(grep -v '^#' config.env | xargs) > /dev/null 2>&1

if [[ ! -z "$USERBOTINDO_ACCESS_TOKEN" ]]; then
    echo "Downloading userbotindo_kit..."
    poetry run pip install git+https://${USERBOTINDO_ACCESS_TOKEN}@github.com/userbotindo/userbotindo_kit@v0.0.5
fi

poetry run anjani
