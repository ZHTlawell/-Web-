#!/bin/zsh

# 以局域网可访问的方式启动 Runzo Web 服务。

set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
log_dir="$project_dir/logs"
log_file="$log_dir/lan_service.log"
host="0.0.0.0"
port="8000"
session_name="runzo_lan"

mkdir -p "$log_dir"

if screen -ls | grep -q "[.]$session_name"; then
  echo "服务已经在运行，screen 会话=$session_name"
  exit 0
fi

cd "$project_dir"
screen -dmS "$session_name" zsh -lc "cd \"$project_dir\" && exec python3 -m uvicorn app.main:app --host \"$host\" --port \"$port\" --loop asyncio --http h11 >> \"$log_file\" 2>&1"

sleep 1

if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "服务启动成功，监听端口=$port"
  echo "日志文件：$log_file"
else
  echo "服务启动失败，请检查日志：$log_file"
  exit 1
fi
