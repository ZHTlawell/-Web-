#!/bin/zsh

# 查看 Runzo Web 的 launchd 托管状态。

set -euo pipefail

label="com.macmini.runzo-web"
plist_path="$HOME/Library/LaunchAgents/$label.plist"
runtime_dir="${RUNZO_RUNTIME_DIR:-$HOME/runzo-web-live}"
user_domain="gui/$(id -u)"

if [[ -f "$plist_path" ]]; then
  echo "已安装 plist：$plist_path"
else
  echo "未发现 plist：$plist_path"
fi

if [[ -d "$runtime_dir" ]]; then
  echo "运行目录：$runtime_dir"
fi

echo
launchctl print "$user_domain/$label" 2>/dev/null || echo "launchd 中未加载 $label"

echo
lsof -nP -iTCP:8000 -sTCP:LISTEN || true
