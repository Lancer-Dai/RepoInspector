# RepoInspector

> GitHub 仓库健康度分析工具 — 输入一个公开仓库 URL，即可看到从 Star、贡献者活跃度、Commit 节奏到 AI 评估报告的全景视图。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Download](https://img.shields.io/badge/%E4%B8%8B%E8%BD%BD-Windows%20v1.0.0-0070f3?logo=windows&logoColor=white)](https://github.com/Lancer-Dai/RepoInspector/raw/main/release/RepoInspector-v1.0.0-windows-x64.zip)

---

## 📑 目录

1. [功能介绍](#-功能介绍)
2. [快速使用](#-快速使用-5-分钟上手)
3. [本地开发](#-本地开发)
4. [打包项目](#-打包项目)
5. [项目结构](#-项目结构)
6. [技术栈](#-技术栈)
7. [常见问题](#-常见问题)

---

## ✨ 功能介绍

**RepoInspector** 是一个本地运行的 Web 工具，帮你快速了解任何公开 GitHub 仓库的状态。

### 核心能力

| 模块 | 能力 |
|---|---|
| **📊 基础指标** | Star / Fork / Watcher 数量、最近活跃时间、License、默认分支、描述 |
| **📈 贡献者分析** | Top 10 贡献者头像、贡献数、占比扇形图（用姓名首字母 fallback 处理匿名用户） |
| **🗓 Commit 节奏** | 近 12 个月每月 commit 数趋势图（识别活跃/停滞期） |
| **💬 Issue 状态** | Open / Closed 总数、Issue 平均响应时间 |
| **🏷 标签分布** | Top 20 label 出现次数、彩色圆环图 |
| **🚀 Releases** | 最近 10 个 release、下载量统计 |
| **🥧 语言分布** | 按代码字节数统计各编程语言占比 |
| **🤖 AI 评估** | 调用大模型（OpenAI 兼容协议）给出项目质量、健康度、风险点的总结报告 |
| **📝 本地历史** | localStorage 保存最近 20 次分析结果，红点提示未读 |
| **⚙ 灵活配置** | UI 内填写 GitHub Token / LLM Key，立即生效 |

### 适合谁用

- 🔍 **技术选型**：快速评估开源项目是否值得集成
- 📋 **代码审查**：在团队内部 Review 前快速了解陌生仓库
- 🤖 **AI 辅助**：让大模型告诉你这个项目的健康度、风险、亮点
- 📚 **学习参考**：研究热门项目的工程实践（贡献者分布、Commit 节奏、Issue 处理）

### 特点

- ✅ **纯本地运行** — 一次打包，终身离线可用
- ✅ **零依赖部署** — 用户拿到 exe 就能跑，无需安装 Python
- ✅ **OpenAI 兼容** — 支持 SiliconFlow / 智谱 / DeepSeek / OpenAI 任意 LLM
- ✅ **Vercel 设计风格** — 黑白基色 + 多色 ECharts，可视化精致
- ✅ **智能端口顺延** — 8000 被占用自动 8001、8002...
- ✅ **可深度定制** — 后端 Python + 前端原生 JS，无复杂构建链

---

## 🚀 快速使用（5 分钟上手）

### 方法 A：下载预编译 exe（推荐普通用户）

| 平台 | 下载 | 大小 |
|---|---|---|
| Windows x64 | [**RepoInspector-v1.0.0-windows-x64.zip**](https://github.com/Lancer-Dai/RepoInspector/raw/main/release/RepoInspector-v1.0.0-windows-x64.zip) | 34.3 MB |

**使用步骤**：

1. 下载上面的 zip，解压到任意文件夹
2. 双击 `RepoInspector.exe`
3. 黑色 console 窗口弹出，显示访问地址（默认 `http://127.0.0.1:8000`）
4. 浏览器**自动打开**该地址
5. 在输入框粘贴一个 GitHub 仓库 URL（如 `https://github.com/python/cpython`），点 **Analyze**
6. （可选）点右上角 ⚙ **Settings** 填入 LLM API Key，点 **🤖 AI 评估** 获取 AI 报告

**关闭服务**：回到 console 窗口按 `Ctrl+C`。

> 💡 所有 releases 历史版本：<https://github.com/Lancer-Dai/RepoInspector/tree/main/release>

### 方法 B：从源码运行（适合开发者）

```bash
git clone https://github.com/Lancer-Dai/RepoInspector.git
cd RepoInspector
pip install -r backend/requirements.txt
python launcher.py
```

浏览器访问 `http://127.0.0.1:8000`。

---

## 🛠 本地开发

### 1. 环境要求

| 工具 | 版本要求 | 说明 |
|---|---|---|
| **Python** | **3.10 或更高** | 后端运行时 |
| **pip** | 21+ | 包管理（Python 自带） |
| **现代浏览器** | Chrome / Edge / Firefox 最近 2 年版本 | 前端 |
| **（可选）Git** | 任意 | 克隆仓库 |
| **（可选）PyInstaller** | 6.10+ | 仅打包时需要 |

> Python 3.9 及以下不支持（`PEP 604` 联合类型语法、`match` 语句等需要 3.10+）。

### 2. 克隆与安装

```bash
# 克隆项目
git clone https://github.com/Lancer-Dai/RepoInspector.git
cd RepoInspector

# 创建虚拟环境（强烈推荐）
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 安装后端依赖
pip install -r backend/requirements.txt
```

如果只想运行（不打包），可以跳过 PyInstaller：

```bash
pip install fastapi uvicorn[standard] httpx pydantic pydantic-settings python-dotenv openai
```

### 3. 配置文件（重要）

**`backend/.env.example` 是模板，复制为 `backend/.env` 后填入真实值。**

```bash
# Windows:
copy backend\.env.example backend\.env
# macOS / Linux:
cp backend/.env.example backend/.env
```

#### 配置项详解

打开 `backend/.env`，逐项填写：

```ini
# ===== GitHub =====
#（可选）Personal Access Token，配置后 API 限流从 60/h 提升到 5000/h
# 生成地址：https://github.com/settings/tokens
# 权限范围：勾选 public_repo 即可
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

REQUEST_TIMEOUT=10          # GitHub API 请求超时（秒）
CACHE_TTL_SECONDS=300       # 内存缓存有效期（秒），避免重复请求

# ===== LLM（用于 AI 评估） =====
#（必填）OpenAI 兼容协议的 API Key
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

#（可选）API 端点，默认 SiliconFlow
LLM_BASE_URL=https://api.siliconflow.cn/v1

#（可选）模型名
LLM_MODEL=Qwen/Qwen3-8B

LLM_TIMEOUT=30              # LLM 调用超时（秒）
LLM_CACHE_TTL_SECONDS=3600  # LLM 评估结果缓存有效期
```

#### 常见 LLM 提供商

| 提供商 | `LLM_BASE_URL` | `LLM_MODEL` 示例 | 注册地址 |
|---|---|---|---|
| **SiliconFlow**（默认） | `https://api.siliconflow.cn/v1` | `Qwen/Qwen3-8B` | https://cloud.siliconflow.cn |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini` | https://platform.openai.com |
| **智谱 BigModel** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | https://bigmodel.cn |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` | https://platform.deepseek.com |
| **本地 Ollama** | `http://localhost:11434/v1` | `qwen2.5` | https://ollama.com |

### 4. 启动开发服务器

#### 方式 A：使用启动脚本（推荐）

```bash
# 端口冲突自动顺延到 8001、8002...
python launcher.py
```

#### 方式 B：直接跑 uvicorn（支持热重载）

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> ⚠️ 方式 B 不会自动开浏览器，也不会做端口顺延。

#### 方式 C：Shell 脚本

```bash
# macOS / Linux
bash backend/run.sh
```

### 5. 调试

启动后浏览器开发者工具（F12）的 Network 面板可以看到所有 API 调用。后端日志会打印每个请求的路径和状态码（除 `?__ping` 心跳外）。

API 文档（FastAPI 自动生成）：
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc:      <http://127.0.0.1:8000/redoc>

主要端点：

| 端点 | 方法 | 用途 |
|---|---|---|
| `/api/analyze` | POST | 主分析接口，body 为 `{"repo_url": "owner/name"}` |
| `/api/ai-review` | POST | 调用 LLM 生成 AI 评估 |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET / PUT | 读取/修改运行时配置（不需要重启） |

### 6. 启动后访问

打开浏览器访问 <http://127.0.0.1:8000>，看到 Vercel 风格的黑色 nav + 输入框即说明成功。

输入框示例：
- ✅ `https://github.com/python/cpython`
- ✅ `python/cpython`
- ✅ `https://github.com/vercel/next.js`

---

## 📦 打包项目

### 1. 打包前置条件

| 工具 | 版本 | 说明 |
|---|---|---|
| **Python** | 3.10+ | 打包机需要 |
| **PyInstaller** | 6.10+ | 打包工具 |
| **Windows** | 10+ | 当前仅在 Windows 平台测试过 |

```bash
# 安装打包依赖
pip install -r backend/requirements.txt
```

### 2. 一键打包

```bash
# 在项目根目录执行
python build.py
```

完成后产物：

```
dist/                                          ← PyInstaller 输出
├── RepoInspector.exe        (~36 MB)          ← 单文件可执行程序
├── README.txt                                 ← 内置中文使用说明
└── .env.example                               ← 配置模板

release/                                       ← 一键分发包
└── RepoInspector-v1.0.0-windows-x64.zip      (~34 MB)
    ├── RepoInspector.exe
    ├── README.txt
    └── .env.example
```

> ✅ `release/` 下的 zip 是给最终用户下载的，里面是干净的三件套。

### 3. 修改版本号

**版本号在两处使用**：
1. **`build.py`** 顶部的 `DEFAULT_VERSION`（默认 `1.0.0`）
2. 打包后的 zip 文件名

#### 方法 A：临时指定版本号

```bash
# 打包成 v2.0.0
python build.py --version 2.0.0
```

输出：`release/RepoInspector-v2.0.0-windows-x64.zip`

#### 方法 B：修改默认值

编辑 [build.py](build.py)：

```python
DEFAULT_VERSION = "1.0.0"   # 改这里
```

下次 `python build.py` 自动用新版本号。

#### 版本号约定（建议遵循 [语义化版本](https://semver.org/lang/zh-CN/)）

| 类型 | 格式 | 何时发布 |
|---|---|---|
| 主版本 | `1.0.0` → `2.0.0` | 不兼容的重大改动 |
| 次版本 | `1.0.0` → `1.1.0` | 新增功能，向后兼容 |
| 修订号 | `1.0.0` → `1.0.1` | Bug 修复 |

### 4. 完整打包选项

| 参数 | 作用 | 示例 |
|---|---|---|
| `--name NAME` | 自定义输出文件名 | `python build.py --name MyTool` |
| `--version X.Y.Z` | 设置版本号（写入 zip 文件名） | `python build.py --version 1.2.0` |
| `--onedir` | 打成文件夹模式（启动更快，便于调试） | `python build.py --onedir` |
| `--no-clean` | 保留上次构建的 dist / build（增量构建） | `python build.py --no-clean` |
| `--no-zip` | 只生成 dist/，不打包 zip | `python build.py --no-zip` |
| `--icon path.ico` | 自定义 exe 图标 | `python build.py --icon D:\my.ico` |
| `--icon ''` | 跳过图标 | `python build.py --icon ''` |

### 5. 跨平台打包

> ⚠️ **当前仅在 Windows 上完整测试过**。其他平台需要在该平台上分别运行 `python build.py`。

| 平台 | 状态 | 备注 |
|---|---|---|
| **Windows x64** | ✅ 已测试 | 产出 `.exe` |
| macOS | ⚠️ 待测试 | 需要在 Mac 上运行 `build.py`，产出 `.app` |
| Linux | ⚠️ 待测试 | 产出 ELF 可执行文件 |

> 不同平台产物的 zip 文件名会带上平台标签，例如 `windows-x64` / `macos-arm64` / `linux-x64`。

### 6. 自定义图标

**方式 A：替换文件**

把项目根目录的 [app.ico](app.ico) 替换为自己的图标文件即可（Windows 需 `.ico` 格式，推荐包含 16/32/48/64/128/256 六个尺寸）。

**方式 B：重新生成**

```bash
# 修改 make_icon.py 中的颜色/形状，然后：
python make_icon.py
```

**方式 C：临时换图标**

```bash
python build.py --icon D:\my-icons\custom.ico
```

### 7. 发布到 GitHub

```bash
# 1. 把所有改动 add + commit
git add .
git commit -m "release: v1.1.0"

# 2. 推送
git push origin main

# 3. 在 GitHub 网页端：
#    Releases → Draft a new release
#    Tag: v1.1.0
#    Upload: release/RepoInspector-v1.1.0-windows-x64.zip
#    Publish
```

> 💡 提示：可以直接在 README 中用 GitHub 原始链接引用 zip 文件：
> ```
> https://github.com/<user>/<repo>/raw/main/release/RepoInspector-v1.1.0-windows-x64.zip
> ```

---

## 📁 项目结构

```
RepoInspector/
├── backend/                       # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # 配置加载
│   │   ├── models.py             # Pydantic 数据模型
│   │   ├── cache.py              # 内存缓存
│   │   ├── github_client.py      # GitHub API 封装
│   │   ├── llm_client.py         # LLM 调用
│   │   ├── analyzer.py           # 仓库分析核心逻辑
│   │   └── routers/
│   │       └── analyze.py        # /api/analyze 路由
│   ├── .env.example              # 配置模板（提交到 git）
│   ├── .gitignore                # 排除 .env
│   ├── requirements.txt          # 依赖清单
│   └── run.sh                    # Unix 启动脚本
│
├── frontend/                      # 原生 HTML/JS 前端（无构建步骤）
│   ├── index.html
│   ├── css/style.css            # Vercel 设计风格
│   └── js/
│       ├── app.js                # 主控制器
│       ├── api.js                # 后端 API 封装
│       ├── charts.js             # ECharts 图表
│       ├── settings.js           # 设置模态框
│       ├── history.js            # 历史记录模态框
│       └── utils.js              # 工具函数
│
├── docs/
│   └── 设计说明书.md              # 中文设计文档
│
├── DESIGN-vercel.md               # Vercel 设计规范（颜色/字体）
│
├── launcher.py                    # 主启动器（端口扫描+banner+开浏览器）
├── build.py                       # PyInstaller + zip 打包
├── make_icon.py                   # 生成 app.ico
│
├── app.ico                        # 应用图标（7 尺寸）
│
├── .gitignore                     # git 排除规则
├── README.md                      # 本文件
│
├── dist/                          # 打包产物（git 忽略）
│   ├── RepoInspector.exe
│   ├── README.txt
│   └── .env.example
│
└── release/                       # 分发包（提交到 git）
    └── RepoInspector-v1.0.0-windows-x64.zip
```

---

## 🧰 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 后端框架 | FastAPI | 0.115+ |
| ASGI 服务器 | Uvicorn | 0.32+ |
| HTTP 客户端 | httpx | 0.28+ |
| 数据校验 | Pydantic | 2.10+ |
| 配置 | pydantic-settings | 2.7+ |
| LLM SDK | openai | 1.60+（兼容任意 OpenAI 协议） |
| 打包 | PyInstaller | 6.10+ |
| 前端图表 | ECharts | 5.x（通过 CDN） |
| 前端 | 原生 HTML + CSS + JavaScript | ES2020+ |

**设计参考**：Vercel 官网的极简黑白色 + 几何无衬线字体。

---

## ❓ 常见问题

### Q: 启动时报端口被占用？
A: 自动顺延到 8001、8002…最多 50 个。如果想强制指定，在 `.env` 加：
```ini
PORT=9000
```

### Q: 打开浏览器是空白页？
A: 检查 console 窗口的输出，看 uvicorn 启动是否成功。常见原因：
- Python 版本 < 3.10
- 依赖未装全（重跑 `pip install -r backend/requirements.txt`）
- 端口被代理软件（Charles、Fiddler）劫持

### Q: AI 评估一直 502？
A: 99% 是 LLM 配置问题。在 Settings 模态框里：
- 确认 `LLM_API_KEY` 已填写
- 确认 `LLM_BASE_URL` 正确（看下面表）
- 确认网络能访问 `LLM_BASE_URL`

### Q: GitHub API 报 403 rate limit？
A: 在 `.env` 填入 `GITHUB_TOKEN` 可提升到 5000 请求/小时。

### Q: 怎么修改 UI 颜色？
A: 改 [frontend/css/style.css](frontend/css/style.css) 顶部的 CSS 变量；改 [frontend/js/charts.js](frontend/js/charts.js) 顶部的 ECharts 调色板。两个文件改完**刷新浏览器**即可（前端是纯静态文件，无构建）。

### Q: 怎么扩展分析维度？
A:
1. 在 [backend/app/github_client.py](backend/app/github_client.py) 加新的 GitHub API 调用
2. 在 [backend/app/models.py](backend/app/models.py) 加新字段
3. 在 [backend/app/routers/analyze.py](backend/app/routers/analyze.py) 编排
4. 在 [frontend/js/app.js](frontend/js/app.js) 调用并渲染
5. 重启后端（前端刷新即可）

### Q: 打包后的 exe 会被杀毒软件拦截？
A: PyInstaller 打的单文件 exe 经常被 360 / 火绒误报。两种解决方式：
- 把 exe 加入白名单
- 用 `python build.py --onedir` 改成文件夹模式（报毒概率低很多）

### Q: 怎么在局域网共享给同事用？
A: 启动时把 host 改为 `0.0.0.0`：
```bash
# 方式 B
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 同事访问 http://<你的IP>:8000
```

### Q: 支持哪些 GitHub 仓库？
A: 任何**公开**仓库。不支持私有仓库（除非额外授权 Token 并修改代码）。

---

## 📜 License

MIT License

## 🙏 致谢

- 设计灵感：[Vercel](https://vercel.com)
- 图表库：[Apache ECharts](https://echarts.apache.org)
- GitHub API：<https://docs.github.com/en/rest>

---

<p align="center">
  Made with ❤️ in pure Python + JavaScript
</p>
