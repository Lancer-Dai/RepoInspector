"""RepoInspector 启动器。

职责：
  1. 解析资源路径（兼容开发模式与 PyInstaller 打包模式）
  2. 加载 .env 配置（优先读取 exe 同级目录）
  3. 打印 ASCII banner 与访问提示
  4. 自动打开默认浏览器
  5. 启动 uvicorn，并把访问日志输出到当前控制台

打包后，用户双击 .exe 即可看到：
  - 一个 console 窗口，内含启动信息和运行时日志
  - 浏览器自动打开 http://127.0.0.1:<port>
"""
from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ============================================================
# 1. 路径解析
# ============================================================
if getattr(sys, "frozen", False):
    # PyInstaller 单文件模式：sys._MEIPASS 是临时解压目录（包含 frontend/ 等资源）
    BUNDLE_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    # 开发模式：launcher.py 位于项目根目录
    BUNDLE_DIR = Path(__file__).resolve().parent
    EXE_DIR = BUNDLE_DIR

# 把 backend 加入 sys.path，使 `import app.main` 能在打包后找到 app 包
_BACKEND_DIR = BUNDLE_DIR / "backend"
if _BACKEND_DIR.is_dir() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 在开发模式下显式 import，触发 PyInstaller 静态分析将 app 打进 bundle；
# 在 PyInstaller 打包模式下 sys.path 已含 _MEIPASS，import 也直接生效。
try:
    import app.main  # noqa: F401  PyInstaller 静态分析依赖
except ImportError as e:
    # 不在 backend 目录结构下，但 launch 服务时会动态 import，这里不报错
    pass

# ============================================================
# 2. 配置加载（.env）
# ============================================================
def _find_env() -> Path | None:
    """按优先级查找 .env：exe 同级 → 项目根 → 临时目录。"""
    candidates = [
        EXE_DIR / ".env",
        BUNDLE_DIR / ".env",
        EXE_DIR.parent / ".env",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


_ENV_PATH = _find_env()
if _ENV_PATH is not None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(_ENV_PATH, override=False)
    except Exception as e:  # dotenv 缺失不应阻止启动
        print(f"[launcher] load .env failed: {e}")

# ============================================================
# 3. 端口（默认 8000；若被占用则自动顺延 8001、8002 ...）
# ============================================================
try:
    DEFAULT_PORT = int(os.environ.get("PORT", "8000"))
except ValueError:
    DEFAULT_PORT = 8000

HOST = os.environ.get("HOST", "127.0.0.1")

# 最多尝试的端口数（含起始端口），防止无限循环
_MAX_PORT_SCAN = 50


def _find_free_port(start: int, host: str = "127.0.0.1") -> int:
    """从 `start` 起，依次尝试 8000→8001→8002 …，返回第一个可绑定的端口。

    实现：每次开一个 socket 尝试 bind；SO_REUSEADDR 减少误判。
    优势：无需启动 uvicorn 才能知道端口是否可用，启动更快。
    """
    for offset in range(_MAX_PORT_SCAN):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                # 该端口已被占用，继续试下一个
                continue
    raise RuntimeError(
        f"No free TCP port found in range {start}..{start + _MAX_PORT_SCAN - 1} on {host}"
    )

# ============================================================
# 4. 控制台 banner
# ============================================================
# Windows 10+ 的 Terminal / 现代 cmd 默认支持 ANSI 颜色；老版本会显示乱码也无碍
_USE_ANSI = sys.platform == "win32" and os.environ.get("WT_SESSION") is not None
_USE_ANSI = _USE_ANSI or sys.platform != "win32"


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_ANSI else text


def print_banner(port: int) -> None:
    bar = _c("36", "─" * 58)  # cyan
    title = _c("1;36", "  RepoInspector — GitHub repository health analyzer")
    label = lambda k, v: f"  {_c('1;32', k):<14} {v}"  # bold green label
    print()
    print(bar)
    print(title)
    print(bar)
    print()
    print(label("Local URL:",    f"http://{HOST}:{port}"))
    if port != DEFAULT_PORT:
        # 起始端口被占用，自动顺延到了别的端口
        notice = _c(
            "33",
            f"  (port {DEFAULT_PORT} was busy, auto-switched to {port})",
        )
        print(label("Note:", notice.lstrip()))
    print(label("Config file:",  str(_ENV_PATH) if _ENV_PATH else "(use built-in defaults)"))
    print(label("Bundle path:",  str(BUNDLE_DIR)))
    print()
    print(_c("33", "  Press Ctrl+C in this window to stop the server."))
    print()
    print(bar)
    print()


# ============================================================
# 5. 日志格式：覆盖 uvicorn 默认的简化输出
# ============================================================
def setup_logging() -> None:
    fmt = "%(asctime)s  %(levelname)-7s  %(name)-20s  %(message)s"
    datefmt = "%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # uvicorn 自身的 loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


# ============================================================
# 6. 自动打开浏览器（延迟 1.5s，等服务真正起来）
# ============================================================
def _open_browser_later(url: str) -> None:
    time.sleep(1.5)
    try:
        if webbrowser.open(url, new=2):
            print(_c("32", f"[launcher] opened browser: {url}"))
        else:
            print(_c("33", f"[launcher] please open manually: {url}"))
    except Exception as e:
        print(_c("33", f"[launcher] please open manually: {url}  ({e})"))


# ============================================================
# 7. 主流程
# ============================================================
def main() -> int:
    setup_logging()

    # 寻找一个空闲端口：8000 被占用就试 8001，依此类推
    try:
        port = _find_free_port(DEFAULT_PORT, HOST)
    except RuntimeError as e:
        print(_c("31", f"\n[launcher] FATAL: {e}"))
        print(
            _c(
                "33",
                f"        set PORT in .env (e.g. PORT=9000) to change the start port.",
            )
        )
        return 2

    url = f"http://{HOST}:{port}"
    print_banner(port)
    threading.Thread(target=_open_browser_later, args=(url,), daemon=True).start()

    try:
        import uvicorn  # noqa: WPS433（运行时导入，确保打包能找到）
    except ImportError:
        print(_c("31", "[launcher] FATAL: uvicorn not installed. pip install -r backend/requirements.txt"))
        return 1

    print(_c("36", f"[launcher] starting uvicorn on {HOST}:{port} ..."))
    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=port,
            log_level="info",
            access_log=True,
        )
    except OSError as e:
        # 极端情况：扫描时端口空闲，启动时被其他进程抢走（端口占用 race condition）
        print(_c("31", f"\n[launcher] FATAL: cannot bind {HOST}:{port} → {e}"))
        print(
            _c(
                "33",
                "        the port became occupied between scan and bind (race condition).",
            )
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(_c("33", "\n[launcher] shutting down (Ctrl+C) ..."))
        sys.exit(0)
