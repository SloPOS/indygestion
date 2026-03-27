#!/usr/bin/env bash
set -euo pipefail
GOOS=linux GOARCH=amd64 go build -o indygestion-agent-linux .
