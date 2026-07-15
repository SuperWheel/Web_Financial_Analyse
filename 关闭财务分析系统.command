#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/scripts/stop-dev.sh"

echo
echo "关闭操作已完成。"
read -r -p "按回车键关闭窗口..."
