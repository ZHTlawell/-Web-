#!/bin/zsh

# 卸载 launchd 登录自启动项，并停止 Runzo Web 服务。

set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
label="com.macmini.runzo-web"
plist_path="$HOME/Library/LaunchAgents/$label.plist"
user_domain="gui/$(id -u)"

launchctl bootout "$user_domain" "$plist_path" >/dev/null 2>&1 || true
rm -f "$plist_path"

"$project_dir/scripts/停止局域网服务.sh" >/dev/null 2>&1 || true

echo "开机自启已卸载：$plist_path"
