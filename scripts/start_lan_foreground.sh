#!/bin/zsh

# ASCII 路径入口，供 launchd 稳定启动 Runzo Web 服务。

set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
host="${RUNZO_HOST:-0.0.0.0}"
port="${RUNZO_PORT:-8000}"
default_python_bin="$project_dir/.venv/bin/python"
if [[ -x "$default_python_bin" ]]; then
  python_bin="${PYTHON_BIN:-$default_python_bin}"
else
  python_bin="${PYTHON_BIN:-/usr/bin/python3}"
fi

cd "$project_dir"
exec "$python_bin" -m uvicorn app.main:app --host "$host" --port "$port" --loop asyncio --http h11
