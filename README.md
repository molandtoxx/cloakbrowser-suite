# CloakBrowser Suite

```
   ____ _       _    ____  _   _ ____            ____  _   _ ____   ___ _____
  / ___| |     / \  |  _ \| | | | __ ) _   _ ___| __ )| | | | __ ) / _ \_   _|
 | |   | |    / _ \ | | | | | | |  _ \| | | / __|  _ \| | | |  _ \| | | || |
 | |___| |___/ ___ \| |_| | |_| | |_) | |_| \__ \ |_) | |_| | |_) | |_| || |
  \____|_____/_/   \_\____/ \___/|____/ \__, |___/____/ \___/|____/ \___/ |_|
                                        |___/
```

跨平台指纹浏览器管理套件。基于 `cloakbrowser` 指纹引擎，为每个浏览器配置文件生成独立的硬件指纹（平台、分辨率、GPU、时区、语言、WebGL、Canvas、音频、字体等），并以**原生系统窗口**启动 Chromium（无需 VNC，无需 Docker）。提供 Web UI 仪表盘与命令行两种操作方式。

---

## 快速开始

### 方式一：本地启动（推荐个人使用）

```bash
# 1. 克隆项目
cd cloakbrowser-suite

# 2. 安装依赖（自动下载 Chromium）
pip install -e .

# 3. 一键启动（自动打开浏览器仪表盘）
python run.py
```

启动后浏览器会自动打开 `http://127.0.0.1:8080`。

### 方式二：服务器模式（推荐局域网/远程管理）

```bash
# 监听所有网络接口，允许局域网内其他设备访问
python run.py --host 0.0.0.0 --port 8080

# 或仅启动服务，不自动打开浏览器
python run.py --no-open
```

---

## 两种使用方式

### Web UI（网页仪表盘）

启动服务后，在浏览器中打开 `http://<服务器IP>:8080`。

支持功能：
- 创建、编辑、删除浏览器配置文件
- 一键启动/停止浏览器（原生窗口）
- 查看实时状态与 CDP 连接信息
- 为配置文件添加标签和备注
- 截图查看浏览器画面

### 命令行（CLI）

安装后全局可用：

```bash
cloakbrowser-suite <命令>
```

CLI 直接调用后端 REST API，适合脚本化操作和远程管理。

---

## 安装说明

### 环境要求

- Python 3.11 或更高版本
- Linux / Windows / macOS
- 桌面环境（Linux 需 X11 或 Wayland）

### 安装步骤

```bash
# 1. 进入项目目录
cd cloakbrowser-suite

# 2. 创建虚拟环境（可选但推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 3. 安装项目（自动安装 cloakbrowser 并下载 Chromium）
pip install -e .

# 4. 启动
python run.py
```

`cloakbrowser[geoip]` 会在首次启动时自动下载所需的 Chromium 二进制文件，无需手动安装 Chrome。

---

## 预构建打包（无需 Python）

如果你不想安装 Python 环境，可以直接下载预构建的独立包，解压即用。

### 下载

从 [GitHub Releases](https://github.com/<your-org>/cloakbrowser-suite/releases) 下载对应平台的压缩包：

| 平台 | 架构 | 文件 |
|------|------|------|
| Linux | x86_64 | `cloakbrowser-suite-linux-x64.tar.gz` |
| macOS | Apple Silicon (M1/M2/M3) | `CloakBrowser-Suite-macOS-arm64.tar.gz` |
| Windows | x86_64 | `cloakbrowser-suite-windows-x64.zip` |

### 使用

```bash
# Linux / macOS
tar xzf cloakbrowser-suite-linux-x64.tar.gz
cd cloakbrowser-suite

# 启动 Web 仪表盘
./cloakbrowser-suite --host 0.0.0.0

# 或使用 CLI
./cloakbrowser-suite profile list
./cloakbrowser-suite browser launch <profile_id>
```

```powershell
# Windows (PowerShell)
Expand-Archive cloakbrowser-suite-windows-x64.zip
cd cloakbrowser-suite

# 启动 Web 仪表盘
.\cloakbrowser-suite.exe --host 0.0.0.0

# 或使用 CLI
.\cloakbrowser-suite.exe profile list
```

> **Chromium 已打包在内**（约 700 MB），首次启动无需下载，解压即用。
>
> 包内包含：Python 运行时 + 全部依赖 + 前端 UI + Chromium 浏览器 + chromedriver。
> 唯一需要网络的是 GeoIP 功能（可选，查询代理 IP 地理位置）。

### 自行打包

如需从源码自行构建独立包（含 Chromium）：

```bash
# 安装构建工具
pip install pyinstaller

# 安装项目依赖（含 cloakbrowser，用于下载 Chromium）
pip install -e .

# 构建前端
cd frontend
npm install && npm run build
cd ..

# 下载 Chromium（cloakbrowser 会下载到 ~/.cloakbrowser/）
python -c "from cloakbrowser.download import ensure_binary; ensure_binary()"

# 打包（Linux / macOS）
pyinstaller build/build.spec --clean --noconfirm

# 打包（Windows - PowerShell）
# pyinstaller build/build.spec --clean --noconfirm
```

或使用一键脚本（会自动完成以上所有步骤）：

```bash
# Linux
bash scripts/build-linux.sh

# macOS
bash scripts/build-macos.sh

# Windows (PowerShell)
.\scripts\build-windows.ps1
```

输出在 `dist/` 目录，结构同下载包一致：

```
dist/cloakbrowser-suite/
├── cloakbrowser-suite          # 主程序（无参数 → 启动 Web UI，有参数 → CLI）
└── _internal/                  # 内含 Python 运行时 + Chromium
    ├── backend/
    ├── cli/
    ├── frontend/dist/
    ├── chromium-146.0.../      # Chromium 浏览器本体 (~700MB)
    │   ├── chrome              # 浏览器可执行文件
    │   ├── chromedriver        # WebDriver
    │   └── locales/            # 多语言资源
    └── ...
```

---

## CLI 命令参考

### 配置文件管理

```bash
# 列出所有配置文件
cloakbrowser-suite profile list

# 按状态筛选
cloakbrowser-suite profile list --status running
cloakbrowser-suite profile list --status stopped

# 按标签筛选
cloakbrowser-suite profile list --tag work --tag urgent

# JSON 输出
cloakbrowser-suite profile list --json

# 创建配置文件（交互式）
cloakbrowser-suite profile create

# 创建时指定参数
cloakbrowser-suite profile create \
  --name "Profile-1" \
  --platform windows \
  --proxy "http://user:pass@host:port" \
  --humanize \
  --geoip

# 查看单个配置文件详情
cloakbrowser-suite profile get <profile_id>

# 更新配置文件
cloakbrowser-suite profile update <profile_id> \
  --name "New Name" \
  --proxy "socks5://host:port"

# 删除配置文件
cloakbrowser-suite profile delete <profile_id>
cloakbrowser-suite profile delete <profile_id> --force  # 跳过确认
```

### 浏览器控制

```bash
# 启动浏览器（打开原生窗口）
cloakbrowser-suite browser launch <profile_id>

# 停止浏览器
cloakbrowser-suite browser stop <profile_id>

# 查看运行中的浏览器
cloakbrowser-suite browser list

# 截图
cloakbrowser-suite browser screenshot <profile_id>
cloakbrowser-suite browser screenshot <profile_id> -o ./capture.png
```

### 服务管理

```bash
# 启动 Web 服务
cloakbrowser-suite start
cloakbrowser-suite start --host 0.0.0.0 --port 9090
cloakbrowser-suite start --no-open  # 不自动打开浏览器

# 查看系统状态
cloakbrowser-suite status
cloakbrowser-suite status --detail    # 显示每个配置文件的详情
```

---

## Web UI 使用

1. 启动服务后，在浏览器访问 `http://127.0.0.1:8080`
2. 点击「新建配置」创建浏览器配置文件
3. 在配置编辑页设置：
   - 基础信息：名称、平台、代理
   - 指纹参数：分辨率、GPU、User-Agent、时区、语言
   - 行为模拟：启用 humanize 模拟真人鼠标/键盘/滚动行为
   - 标签与备注：方便分类管理
   - 启动参数：自定义 Chromium 命令行参数
4. 保存后点击「启动」按钮，浏览器将以原生窗口打开
5. 启动后可查看 CDP 连接地址，用于自动化脚本接入

---

## 配置文件与数据目录

所有数据默认存储在平台对应的应用数据目录：

| 平台 | 默认路径 |
|------|----------|
| Linux | `~/.local/share/cloakbrowser-suite/` |
| macOS | `~/Library/Application Support/CloakBrowser Suite/` |
| Windows | `~/AppData/Local/CloakBrowser Suite/` |

目录内容：
- `profiles.db` — SQLite 数据库（配置文件信息）
- `profiles/<uuid>/` — 各配置文件的 Chromium 用户数据目录

可通过环境变量自定义数据目录：

```bash
export CLOAKBROWSER_DATA_DIR=/path/to/data
python run.py
```

---

## 远程访问

默认只监听 `127.0.0.1`，仅本机可访问。如需局域网内其他设备管理：

```bash
# 监听所有接口
python run.py --host 0.0.0.0

# 或
cloakbrowser-suite start --host 0.0.0.0 --port 8080
```

然后在其他设备的浏览器中访问 `http://<服务器局域网IP>:8080`。

如需身份验证，设置环境变量：

```bash
export AUTH_TOKEN=your-secret-token
python run.py --host 0.0.0.0
```

访问时需在登录页输入 Token，或通过 CLI 设置：

```bash
export CLOAKBROWSER_AUTH_TOKEN=your-secret-token
cloakbrowser-suite profile list
```

---

## 自动化（CDP）

每个运行中的浏览器都暴露 Chrome DevTools Protocol（CDP）端点，可通过 Playwright、Puppeteer、Selenium 等工具连接。

### Playwright 示例

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 通过 CloakBrowser Suite 的 CDP 代理连接
    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:8080/api/profiles/<profile_id>/cdp"
    )
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()

    page.goto("https://example.com")
    page.screenshot(path="screenshot.png")
    browser.close()
```

### 获取 CDP 信息

```bash
curl http://127.0.0.1:8080/api/profiles/<profile_id>/cdp
```

返回 WebSocket 调试地址和连接示例。

### 剪贴板操作（CDP 方式）

```bash
# 向浏览器写入文本
curl -X POST http://127.0.0.1:8080/api/profiles/<profile_id>/clipboard \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World"}'

# 读取浏览器当前选中文本
curl http://127.0.0.1:8080/api/profiles/<profile_id>/clipboard
```

---

## 常见问题

**Q: 启动时提示找不到 Chromium？**

A: `cloakbrowser` 会在首次使用时自动下载 Chromium。如果下载失败，检查网络连接，或手动设置 `CLOAKBROWSER_DATA_DIR` 到有写权限的目录。

**Q: Linux 上浏览器窗口没有弹出？**

A: 确保当前会话有图形环境。检查 `DISPLAY` 环境变量是否设置：

```bash
echo $DISPLAY
# 应输出类似 :0 或 :1
```

如果通过 SSH 连接，需使用 X11 转发（`ssh -X`）或在本地桌面终端运行。

**Q: 如何同时运行多个配置文件？**

A: 每个配置文件有独立的用户数据目录和指纹，可以同时启动多个。通过 Web UI 或 CLI 分别启动即可。

**Q: 如何备份配置文件？**

A: 备份数据目录即可：

```bash
# Linux
cp -r ~/.local/share/cloakbrowser-suite /backup/path

# 恢复
cp -r /backup/path/cloakbrowser-suite ~/.local/share/
```

**Q: 支持哪些代理类型？**

A: HTTP、HTTPS、SOCKS5。格式示例：
- `http://user:pass@host:port`
- `socks5://host:port`

**Q: 启用 GeoIP 后时区和语言会自动设置吗？**

A: 是的。开启 `--geoip` 后，系统会根据代理 IP 的地理位置自动推断时区和语言，并应用到浏览器指纹中。

**Q: 如何设置开机自动启动某个配置文件？**

A: 在创建或更新配置文件时启用 `auto_launch`：

```bash
cloakbrowser-suite profile create --name "Auto" --auto-launch
```

服务启动时会自动打开标记为 auto-launch 的配置文件。

**Q: 如何完全重置所有数据？**

A: 停止服务后删除数据目录：

```bash
rm -rf ~/.local/share/cloakbrowser-suite
```

下次启动时会自动重新初始化。

---

## 技术栈

- 后端：FastAPI + Uvicorn + SQLite
- 前端：React + Vite + Tailwind CSS
- 浏览器引擎：cloakbrowser + Playwright
- CLI：Click

---

## License

MIT
