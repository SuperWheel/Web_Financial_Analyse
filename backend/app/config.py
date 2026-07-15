"""应用配置。

单机本地部署，配置项少而稳定。如未来需要环境化，可切换为 pydantic-settings BaseSettings。
"""
from __future__ import annotations

from pathlib import Path

# 项目根目录（backend/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# SQLite 数据库文件落地于项目根 data/ 目录
DATA_DIR = PROJECT_ROOT / "data"
IMPORTS_DIR = DATA_DIR / "imports"
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMPORTS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "finance.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# 后端监听端口（默认 9000：避开 Windows Hyper-V 保留端口范围 7985-8084 / 8134-8233，
# 该范围会把常见的 8000/8080 等端口排除，导致 bind 报 Errno 13）
BACKEND_PORT = 9000

# CORS：开发期允许前端 Vite dev server 访问
BACKEND_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
]

# API 前缀
API_PREFIX = "/api"
