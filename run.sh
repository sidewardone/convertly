#!/usr/bin/env bash
# Запуск из исходников без установки.
set -euo pipefail
cd "$(dirname "$0")"
exec env PYTHONPATH=src python3 -m convertly "$@"
