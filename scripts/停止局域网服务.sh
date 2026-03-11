#!/bin/zsh

# 停止以后台方式运行的 Runzo Web 服务。

set -euo pipefail

session_name="runzo_lan"
port="8000"

if screen -ls | grep -q "[.]$session_name"; then
  screen -S "$session_name" -X quit
fi

listen_pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN || true)"
if [[ -n "$listen_pid" ]]; then
  kill $listen_pid
  echo "已停止服务，端口=$port"
else
  echo "未发现监听进程，服务可能未启动。"
fi
