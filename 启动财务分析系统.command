#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/scripts/start-dev.sh"

echo
echo "服务已启动。关闭本窗口不会停止服务；日志位于 .runtime 目录。"
echo "如需重新查看地址，请再次双击本启动项。"
read -r -p "按回车键关闭窗口..."
