#!/bin/sh

URL=$1
shift
XAPIKEY=$1
shift



for i in $@; do
    echo $i;
    curl -d "@$i" -H "X-Api-Key: ${XAPIKEY}" -H "Accept: application/json" -H "Content-Type: application/json" -X PUT "${URL}";
done
