#!/usr/bin/env bash
set -euo pipefail
GOOS=darwin GOARCH=amd64 go build -o indygestion-agent-mac .
