# RepoInspector
提供 web 页面，用户输入某个公开 Github 仓库的 url，对这个仓库进行分析并用可视化的形式展示相关指标（如Star数，Fork数，编程语言分布等）。

## 打包为单文件 exe（无需 Python 环境即可运行）

```bash
# 1) 安装打包依赖（仅打包机需要）
pip install -r backend/requirements.txt

# 2) 在项目根目录执行
python build.py
```

完成后在 `dist/RepoInspector.exe` 得到单文件可执行程序。**双击它**即可：

- 弹出一个黑色 console 窗口，展示启动 banner、访问地址、运行时访问日志
- 自动打开默认浏览器到 http://127.0.0.1:8000
- **端口冲突自动顺延**：默认 8000；若被占用则自动用 8001、8002…（最多尝试 50 个），banner 顶部会显示 `Note: (port 8000 was busy, auto-switched to 8001)`
- 想关闭服务，回到 console 窗口按 `Ctrl+C`

最终用户分发只需：

```
dist/
├── RepoInspector.exe        ← 主程序
├── README.txt               ← 使用说明
└── .env.example             ← 配置模板（可选）
```

把 `dist/` 整个文件夹拷给用户即可。用户的 `.env` 放在 `RepoInspector.exe` 同级目录，会自动被加载（无需重启电脑，关闭再开即可）。

打包选项：

| 参数 | 作用 |
|---|---|
| `--onedir` | 打成文件夹（启动更快，便于调试） |
| `--name MyApp` | 自定义输出文件名 |
| `--no-clean` | 保留上次构建的 dist / build |
| `--icon path.ico` | 自定义 exe 图标（Windows 需 .ico；macOS 需 .icns）<br>默认使用项目根目录的 `app.ico`<br>传空字符串 `--icon ''` 跳过图标 |

### 自定义图标
- 替换项目根目录的 `app.ico` 即可（推荐含 16/32/48/64/128/256 多尺寸图层）
- 重新生成：在 Python 环境跑 `python make_icon.py`
- 临时换图标：`python build.py --icon D:\my-icons\custom.ico`

