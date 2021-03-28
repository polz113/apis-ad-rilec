#!/bin/sh

API_KEY=$1

./get_data_from_production.sh "${API_KEY}" > ./apis_dump.json && rm dumps/*; ./unpack_data_dump.py
