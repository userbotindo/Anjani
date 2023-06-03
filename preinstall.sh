#!/bin/bash

if [[ ! -z "$USERBOTINDO_ACCESS_TOKEN" ]]; then
    echo "Downloading userbotindo_kit..."
    poetry run pip install git+https://${USERBOTINDO_ACCESS_TOKEN}@github.com/userbotindo/userbotindo_kit@v0.1.2
fi
