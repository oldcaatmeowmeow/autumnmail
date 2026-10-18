# 秋信 · AutumnMail

> 把秋招的每一封信，变成清晰的下一步。

秋信（AutumnMail）是一个本地优先的秋招邮件 Agent：从 **QQ / 网易 163**（后续 Outlook）中自动筛出公司、面试时间、面试类型、测评与拒信，整理成一条可追踪的时间线。

> 当前进度：**M1 · 真实 IMAP 接入（QQ / 163 只读）**。桌面壳、本地 API、SQLite、完整 UI、连接校验与增量同步已打通；中文秋招解析与事件生成在 M2 接入。

---

## 现在能做什么（M1）

- 一个可启动的 **Windows 桌面窗口**（pywebview + WebView2，失败时回退 Edge 应用窗口）。
- 本地 FastAPI 服务，仅监听 `127.0.0.1`，随机端口 + 启动令牌校验。
- SQLite 自动建库与**增量迁移**，首次启动写入合成演示数据（7 家公司、13 个事件）。
- **真实 QQ / 163 IMAP 接入**：
  - 添加邮箱前先测试连接，失败时给出可操作的错误提示。
  - 只读拉取：`BODY.PEEK[]` + 只读收件箱，不标记已读、不移动、不删除。
  - 按 UID 去重，增量同步；账户显示已同步邮件数与上次同步时间。
  - 手动同步（顶部按钮 / 账户行）与后台定时同步（默认每 15 分钟）。
- 完整 UI：
  - **仪表盘**：今日/未来 7 天、待处理、本周拒信、最近动态
  - **机会列表**：筛选、搜索、按最近安排排序
  - **机会详情**：时间线、证据句、原邮件摘要、标记完成/忽略
  - **日历**：月视图 + 本月安排 + 导出 `.ics`
  - **审核队列**：低置信度邮件的人工确认与纠正
  - **设置**：邮箱账户、连接测试、同步、AI 服务商/Key、扫描频率、通知、数据导出/重置
- **三步首次向导**：邮箱 → AI → 开始；可先看演示数据。
- 密钥使用 **Windows DPAPI** 加密，不写入日志或导出文件。
- 导出 CSV / ICS。

## 尚未接入（M2+）

- 中文秋招规则包 + LLM 结构化抽取（把已同步邮件变成机会/事件）。
- Windows Toast、托盘常驻、开机自启。
- Outlook / Microsoft Graph（二期）。
- 正式安装包（Nuitka + Inno Setup）。

> 说明：M1 只负责“把邮件安全地拉进本地库”。仪表盘上的机会与事件仍来自演示数据，直到 M2 完成解析。

---

## 快速开始

### 一键开发启动

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

脚本会创建 `.venv`、安装依赖、构建前端并启动桌面窗口。

### 手动启动

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 构建前端（首次或改动前端后）
powershell -ExecutionPolicy Bypass -File .\scripts\build_web.ps1

# 启动桌面应用
.\.venv\Scripts\python.exe -m autumnmail
```

### 只启动本地服务（调试 / 浏览器）

```powershell
$env:AUTUMNMAIL_TOKEN = "dev-token"
.\.venv\Scripts\python.exe -m autumnmail --no-window --dev --port 8765
# 打开 http://127.0.0.1:8765/#token=dev-token
```

`--dev` 会开启 `/docs` 与调试日志。`AUTUMNMAIL_TOKEN` 仅用于本地开发；正式启动每次随机生成。

### 前端热更新

```powershell
# 终端 1：后端固定 8765
$env:AUTUMNMAIL_TOKEN = "dev-token"
.\.venv\Scripts\python.exe -m autumnmail --no-window --dev --port 8765

# 终端 2
cd web
npm run dev
# 打开 http://127.0.0.1:5173/#token=dev-token
```

---

## 数据与隐私

| 项 | 位置 |
|---|---|
| 数据库 | `%LOCALAPPDATA%\AutumnMail\data.db` |
| 加密密钥 | `%LOCALAPPDATA%\AutumnMail\secrets.json`（DPAPI） |
| 日志 / 导出 / 备份 | `%LOCALAPPDATA%\AutumnMail\{logs,exports,backups}` |

- 本地 API 只绑定 `127.0.0.1`，所有 `/api` 请求需要启动令牌。
- 授权码 / API Key 使用 **Windows DPAPI（当前用户）** 加密；明文不落盘。
- 邮件读取使用只读方式（`BODY.PEEK[]` + 只读收件箱），不标记已读、不移动、不删除。
- 不会上传邮箱内容；LLM 只接收进入判定的邮件（M2 接入）。

---

## 项目结构

```
autumnmail/
├─ __main__.py            # python -m autumnmail
├─ desktop.py             # pywebview / Edge 回退、单实例、调度器生命周期
├─ server.py              # FastAPI 应用、静态资源、SPA 回退
├─ api/                   # REST 路由与令牌依赖
├─ store/                 # SQLite 连接、schema、迁移、仓库层
├─ core/                  # IMAP 连接器、同步、调度、provider 预设、ICS
├─ security/              # DPAPI、令牌
└─ web/                   # 前端构建产物（npm run build 生成）
web/                      # Vue 3 + Vite 源码
scripts/                  # dev / build_web / build_exe
tests/                    # API / 解析 / 同步测试
```

### 架构

```
pywebview (WebView2)
      │  HTTP + X-App-Token
      ▼
FastAPI (127.0.0.1:随机端口)
      │
      ├─ SQLite (data.db)
      └─ Core: IMAP Connector → Sync → SQLite；rules/LLM（M2）→ store → export
```

---

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前覆盖（21 项）：健康检查、令牌校验、演示数据、机会排序、仪表盘、审核处理、CSV/ICS 导出、设置与密钥脱敏、账户校验、事件状态、邮件解析（纯文本/HTML）、IMAP 日期格式、错误映射、同步去重与账户计数。

---

## 路线图

| 阶段 | 内容 |
|---|---|
| **M0 ✅** | 桌面壳 + 本地服务 + SQLite + 完整 UI + 演示数据 + 测试 |
| **M1 ✅** | QQ/163 IMAP 只读接入、真实连接校验、增量拉取、后台调度 |
| **M2** | 中文秋招规则包 + LLM 结构化抽取 + 审核反馈闭环 |
| **M3** | 日历/ICS 完善、Toast、托盘/自启、导出备份 |
| **M4** | Nuitka 打包 + 安装包 + 首启体验 + 文档 |
| **M5** | Outlook / Microsoft Graph、本地 Ollama、自动更新 |

---

## 已知限制

- M1 首次启动仍会直接进入**演示仪表盘**；三步首次向导可从「设置 → 重新体验首次向导」进入（M2 接入解析后会改为首启自动进入向导）。
- M1 的仪表盘机会/事件仍来自演示数据；真实邮件已同步到本地库，但解析与事件生成在 M2。
- 添加 QQ/163 前，需要先在邮箱后台开启 IMAP 并生成授权码。
- Outlook 识别后提示"二期支持"。
- 未签名 exe 可能触发 SmartScreen；正式发布前需要代码签名。

---

## 分支约定

- `main`：验收通过、可发布的版本。
- `dev`：日常开发分支。功能、修复先提交到 `dev`，再通过 Pull Request 合入 `main`。
- 首次提交已同时创建并推送 `dev` 分支；后续开发从 `dev` 拉分支或直接在 `dev` 提交。

