"""FastAPI 入口。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import analyze

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

app = FastAPI(
    title="RepoInspector",
    description="GitHub 仓库健康度分析工具",
    version="1.0.0",
)

# CORS：开发期允许本地前端；生产环境建议改为同源或限制白名单
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api", tags=["analyze"])


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


# 托管前端静态文件
# 同时支持开发模式（从项目目录读取）和 PyInstaller 打包模式（从临时解压根目录读取）
def _resolve_frontend_dir() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller 打包：资源在 sys._MEIPASS（临时目录）
        return Path(sys._MEIPASS) / "frontend"
    # 开发模式：backend/app/main.py → ../../../
    return Path(__file__).resolve().parent.parent.parent / "frontend"


_FRONTEND_DIR = _resolve_frontend_dir()
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logging.warning("前端目录不存在: %s（请确认 frontend/ 与 backend/ 同级）", _FRONTEND_DIR)
