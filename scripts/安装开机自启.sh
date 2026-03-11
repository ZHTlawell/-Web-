#!/bin/zsh

# 安装 launchd 登录自启动项，并立即启动 Runzo Web 服务。

set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
launch_agents_dir="$HOME/Library/LaunchAgents"
label="com.macmini.runzo-web"
plist_path="$launch_agents_dir/$label.plist"
runtime_dir="${RUNZO_RUNTIME_DIR:-$HOME/runzo-web-live}"
stdout_log="$runtime_dir/logs/launchd_service.log"
stderr_log="$runtime_dir/logs/launchd_service.err.log"
user_domain="gui/$(id -u)"

mkdir -p "$launch_agents_dir" "$project_dir/logs" "$runtime_dir"

rsync -a --delete \
  --exclude '.venv' \
  --exclude 'logs' \
  --exclude 'output' \
  "$project_dir/" "$runtime_dir/"

if [[ ! -x "$runtime_dir/.venv/bin/python" ]]; then
  python3 -m venv "$runtime_dir/.venv"
fi
"$runtime_dir/.venv/bin/pip" install -r "$runtime_dir/requirements.txt" >/dev/null

if [[ -x "$runtime_dir/.venv/bin/python" ]]; then
  python_bin="${PYTHON_BIN:-$runtime_dir/.venv/bin/python}"
else
  python_bin="${PYTHON_BIN:-/usr/bin/python3}"
fi

cat >"$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$python_bin</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>app.main:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>8000</string>
    <string>--loop</string>
    <string>asyncio</string>
    <string>--http</string>
    <string>h11</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$runtime_dir</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$stdout_log</string>
  <key>StandardErrorPath</key>
  <string>$stderr_log</string>
</dict>
</plist>
EOF

chmod 644 "$plist_path"
chmod +x "$project_dir/scripts/前台启动局域网服务.sh" "$project_dir/scripts/start_lan_foreground.sh"

"$project_dir/scripts/停止局域网服务.sh" >/dev/null 2>&1 || true

launchctl bootout "$user_domain" "$plist_path" >/dev/null 2>&1 || true
launchctl bootstrap "$user_domain" "$plist_path"
launchctl kickstart -k "$user_domain/$label"

for _ in {1..10}; do
  if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "开机自启已安装并启动成功"
    echo "plist：$plist_path"
    echo "运行目录：$runtime_dir"
    echo "日志：$stdout_log"
    exit 0
  fi
  sleep 1
done

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "开机自启已安装并启动成功"
  echo "plist：$plist_path"
  echo "运行目录：$runtime_dir"
  echo "日志：$stdout_log"
else
  echo "launchd 已安装，但服务未成功监听 8000，请检查日志：$stderr_log"
  exit 1
fi
