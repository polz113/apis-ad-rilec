#!/bin/sh

URL="https://apis-rilec-php.fri1.uni-lj.si/hr/HRMaster/replicate"

XAPIKEY=$1

curl -H "X-Api-Key: ${XAPIKEY}" -H "Accept: application/json" -H "Content-Type: application/json" -X GET "${URL}";
