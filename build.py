"""一键打包脚本：把整个 RepoInspector 打成单个 .exe + 分发 zip。

用法（在项目根目录执行）：
    python build.py

产物：
    dist/RepoInspector.exe              ← 单文件可执行程序
    dist/.env.example                   ← 配置文件模板
    dist/README.txt                     ← 最终用户使用说明
    release/RepoInspector-v1.0.0-windows-x64.zip   ← 一键分发包

也可以带参数自定义：
    python build.py --name MyApp --onedir --version 2.0.0
"""
from __future__ import annotations

import argparse
import datetime as _dt
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_DIR = PROJECT_ROOT
RELEASE_DIR = PROJECT_ROOT / "release"
ENV_EXAMPLE = PROJECT_ROOT / "backend" / ".env.example"

# 默认版本号；通过 --version 覆盖
DEFAULT_VERSION = "1.0.0"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}\n  (cwd={cwd or PROJECT_ROOT})")
    subprocess.run(cmd, cwd=str(cwd or PROJECT_ROOT), check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build RepoInspector as a single .exe")
    ap.add_argument("--name", default="RepoInspector", help="output executable name")
    ap.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help=f"version string embedded in the release zip name (default: {DEFAULT_VERSION})",
    )
    ap.add_argument(
        "--onedir",
        action="store_true",
        help="produce a folder instead of single file (faster startup, easier to debug)",
    )
    ap.add_argument(
        "--no-clean",
        action="store_true",
        help="skip cleaning previous build/dist directories",
    )
    ap.add_argument(
        "--no-zip",
        action="store_true",
        help="skip creating the release zip (only produce the raw exe in dist/)",
    )
    ap.add_argument(
        "--icon",
        default=str(PROJECT_ROOT / "app.ico"),
        help="path to .ico file (Windows) / .icns (macOS). Pass '' to skip the icon. "
             f"Default: {PROJECT_ROOT / 'app.ico'}",
    )
    args = ap.parse_args()

    if not FRONTEND_DIR.is_dir():
        print(f"[build] FATAL: frontend directory not found: {FRONTEND_DIR}")
        return 1

    # ------------------------------------------------------------------
    # 1) 确保 pyinstaller 已安装
    # ------------------------------------------------------------------
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[build] PyInstaller not found. Installing ...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # ------------------------------------------------------------------
    # 2) 清理上一次的产物
    # ------------------------------------------------------------------
    if not args.no_clean:
        for d in (BUILD_DIR, DIST_DIR):
            if d.exists():
                print(f"[build] cleaning {d}")
                shutil.rmtree(d, ignore_errors=True)
        # 删除旧 spec（避免名称冲突）
        old_spec = SPEC_DIR / f"{args.name}.spec"
        if old_spec.exists():
            old_spec.unlink()

    # ------------------------------------------------------------------
    # 3) 组装 pyinstaller 命令
    # ------------------------------------------------------------------
    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--console",                # 保留控制台窗口，让用户看到日志
        f"--name={args.name}",
        # 把 backend 加入模块搜索路径（让 `import app.main` 生效）
        f"--paths={PROJECT_ROOT / 'backend'}",
        # 显式声明隐藏的导入：app 包及其子模块（PyInstaller 静态分析无法追踪 uvicorn.run 里的动态字符串导入）
        "--hidden-import", "app.main",
        "--hidden-import", "app.routers",
        "--hidden-import", "app.routers.analyze",
        "--hidden-import", "app.analyzer",
        "--hidden-import", "app.cache",
        "--hidden-import", "app.config",
        "--hidden-import", "app.github_client",
        "--hidden-import", "app.llm_client",
        "--hidden-import", "app.models",
        # 把 frontend/ 整个目录作为数据打进 bundle
        # Windows 下 src;dest；其他平台 src:dest
        "--add-data",
        f"{FRONTEND_DIR}{(';' if sys.platform == 'win32' else ':')}frontend",
        # uvicorn 含 watchgod/websockets 等子依赖，PyInstaller 容易漏，
        # 用 --collect-all 一并打包最稳
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "fastapi",
        # 排除无用的大包，减小体积
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "numpy",
        "--exclude-module",
        "pandas",
        # 入口脚本
        str(PROJECT_ROOT / "launcher.py"),
    ]

    # 自定义图标：仅在指定了有效文件时插入 --icon
    icon_path = Path(args.icon) if args.icon else None
    if icon_path and icon_path.is_file():
        cmd.extend(["--icon", str(icon_path)])
        print(f"[build] using icon: {icon_path}")
    elif args.icon:
        print(f"[build] WARN: icon file not found: {args.icon} (skipping --icon)")

    if args.onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    # ------------------------------------------------------------------
    # 4) 执行打包
    # ------------------------------------------------------------------
    print("[build] running PyInstaller ...")
    run(cmd)

    # ------------------------------------------------------------------
    # 5) 复制 .env.example 到 dist/，方便用户立即配置
    # ------------------------------------------------------------------
    if ENV_EXAMPLE.is_file():
        target = DIST_DIR / ".env.example"
        if args.onedir:
            target = DIST_DIR / args.name / ".env.example"
        shutil.copy2(ENV_EXAMPLE, target)
        print(f"[build] copied {ENV_EXAMPLE.name} -> {target}")

    # ------------------------------------------------------------------
    # 6) 写一份 README 给最终用户
    # ------------------------------------------------------------------
    readme = DIST_DIR / ("README.txt" if not args.onedir else f"{args.name}/README.txt")
    readme.write_text(
        "RepoInspector\n"
        "============\n\n"
        f"运行方式：双击 {args.name}.exe\n\n"
        "启动后会自动打开浏览器；如未自动打开请手动访问控制台窗口中显示的地址。\n"
        "默认监听 127.0.0.1:8000；若端口被占用会自动顺延到 8001、8002 ...\n\n"
        "配置：\n"
        "  - 把 .env.example 复制为 .env 放在本 exe 同级目录\n"
        "  - 修改其中的 GITHUB_TOKEN / LLM_API_KEY / LLM_BASE_URL / LLM_MODEL\n"
        "  - 重启 exe 即可生效\n\n"
        "或者：在 UI 中点击右上角 ⚙ 按钮配置，会立即生效（仅当前浏览器）\n\n"
        "关闭服务：在弹出的黑色窗口中按 Ctrl+C\n",
        encoding="utf-8",
    )
    print(f"[build] wrote {readme}")

    # ------------------------------------------------------------------
    # 7) 打包为 zip 方便分发
    # ------------------------------------------------------------------
    if args.no_zip:
        print("[build] --no-zip specified, skipping release zip")
    else:
        package_zip(
            name=args.name,
            version=args.version,
            onedir=args.onedir,
        )

    # ------------------------------------------------------------------
    # 8) 完成
    # ------------------------------------------------------------------
    print("\n[build] DONE.")
    if not args.onedir:
        print(f"[build] artifact: {DIST_DIR / (args.name + '.exe')}")
    else:
        print(f"[build] artifact: {DIST_DIR / args.name}")
    return 0


# ============================================================
# zip 打包：把 exe + README.txt + .env.example 合成一个 zip
# ============================================================
def _platform_tag() -> str:
    """生成平台标签，例如 'windows-x64' / 'macos-arm64'。"""
    sys_map = {"win32": "windows", "darwin": "macos", "linux": "linux"}
    os_name = sys_map.get(sys.platform, sys.platform)
    arch = platform.machine().lower()
    # 归一化常见架构名
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(arch, arch)
    return f"{os_name}-{arch}"


def package_zip(name: str, version: str, onedir: bool) -> Path:
    """把 dist/{name}.exe、README.txt、.env.example 合成一个 zip。

    zip 文件命名：release/RepoInspector-v{version}-{platform}-{arch}.zip
    zip 内文件结构（用户解压即用）：
        RepoInspector.exe
        README.txt
        .env.example
    """
    RELEASE_DIR.mkdir(exist_ok=True)
    # 清掉旧版本的 zip（同名或同版本号），避免历史堆积
    for old in RELEASE_DIR.glob(f"{name}-v*.zip"):
        print(f"[build] removing old release: {old.name}")
        old.unlink()

    platform_tag = _platform_tag()
    zip_path = RELEASE_DIR / f"{name}-v{version}-{platform_tag}.zip"

    # 待打包的文件列表：(源路径, zip 内相对名)
    files: list[tuple[Path, str]] = []
    if onedir:
        # onedir 模式：把整个目录里的内容（含 exe、_internal 资源、README、.env.example）压进 zip
        src_dir = DIST_DIR / name
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                files.append((f, f.relative_to(src_dir).as_posix()))
    else:
        # onefile 模式：3 个文件
        files.append((DIST_DIR / f"{name}.exe", f"{name}.exe"))
        for extra in ("README.txt", ".env.example"):
            p = DIST_DIR / extra
            if p.is_file():
                files.append((p, extra))

    if not files:
        print(f"[build] WARN: no files found to zip in {DIST_DIR} — skipping zip")
        return zip_path

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for src, arcname in files:
            zf.write(src, arcname)
            print(f"[build]   + {arcname}  ({src.stat().st_size:,} bytes)")

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"[build] packed: {zip_path}  ({size_mb:.2f} MB)")
    return zip_path


if __name__ == "__main__":
    sys.exit(main())
