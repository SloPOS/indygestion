#!/usr/bin/env bash
set -euo pipefail
GOOS=windows GOARCH=amd64 go build -o indygestion-agent.exe .
