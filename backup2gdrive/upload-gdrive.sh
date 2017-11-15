#! /bin/bash

folder="0B45NZWirogVWejJZMmRwSVoyT28"

auth-url="https://accounts.google.com/o/oauth2/v2/auth"
clientid="107696934743096388298"
tokenuri="https://accounts.google.com/o/oauth2/token"

curl -X POST \
        -H "Accept: application/json" \
        -H "Content-Type: application/json" \
        -d "uploadType=resumable"  \
        https://www.googleapis.com/upload/drive/v3/files
