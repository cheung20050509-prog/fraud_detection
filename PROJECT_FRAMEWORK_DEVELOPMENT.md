# 项目框架与开发说明

## 文档目的

这份文档从两个角度总结当前仓库：

- framework：项目使用了什么技术框架，整体是怎样组织的
- development：项目平时如何启动、调试、开发和维护

这份文档适合用于：

- 新成员快速上手
- 项目技术梳理
- 给 VS Code 智能体或其他 AI 助手提供上下文

## 项目定位

Fraud Blocking System 是一个面向电信诈骗防护场景的应用系统，核心业务主要分成三条主线：

- AI 陪练：模拟诈骗场景，对用户进行反诈训练
- 实时监护：对实时音频流进行风险监听和预警
- 案例分析：对上传音频或文件进行离线分析

项目整体采用前后端分离结构：

- frontend：负责页面展示、交互流程和用户操作
- backend：负责 API、WebSocket、AI 能力、音频处理和数据访问

## 项目框架总结

### 前端框架

前端是一个基于 Vue 3 的单页应用。

- 核心框架：Vue 3
- 开发与构建工具：Vite
- 语言：TypeScript
- 路由：Vue Router
- 状态管理：Pinia
- 常用工具：VueUse、Axios
- UI 辅助：lucide-vue-next、clsx、tailwind-merge
- 样式体系：Tailwind CSS
- 前端规范工具：ESLint、Prettier

主要页面位于：

- `frontend/src/pages/HomePage.vue`
- `frontend/src/pages/PracticePage.vue`
- `frontend/src/pages/MonitorPage.vue`
- `frontend/src/pages/AnalysisPage.vue`
- `frontend/src/pages/SettingsPage.vue`

### 后端框架

后端是一个基于 FastAPI 的服务端应用，通过 Uvicorn 启动。

- Web/API 框架：FastAPI
- 运行服务器：Uvicorn
- 配置与校验：Pydantic、pydantic-settings
- ORM 与数据库：SQLAlchemy、Alembic
- 异步与网络：websockets、aiortc、aiofiles、httpx
- 日志与监控：标准 logging、loguru、prometheus-client

后端主入口文件：

- `backend/app/main.py`

后端按业务能力拆分为多个路由模块：

- `backend/app/routers/ai_practice.py`
- `backend/app/routers/monitoring.py`
- `backend/app/routers/analysis.py`
- `backend/app/routers/config.py`

### AI 与音频处理栈

这个项目不是普通的 Web CRUD 系统，核心价值依赖 AI 推理和音频处理能力。

- 模型运行基础：PyTorch、Transformers
- 多模态音频模型相关：Qwen2Audio 相关栈
- ASR 语音识别：Whisper、FunASR
- 模型分发与加载：ModelScope、Hugging Face Hub
- TTS 语音合成：edge-tts
- 音频预处理：librosa、soundfile、numpy、scipy、pyaudio

这意味着后端同时承担了：

- Web 服务能力
- 音频处理能力
- 模型推理能力
- 风险评估能力

## 核心业务结构

### 1. AI 陪练模块

AI 陪练模块负责模拟诈骗对话场景，让用户通过文本或语音进行反诈训练。

主要职责：

- 创建场景化陪练会话
- 处理用户文本或语音输入
- 生成模拟诈骗方回复
- 评估用户反诈表现并生成总结报告

主要实现区域：

- `backend/app/services/ai_chat.py`

### 2. 实时监护模块

实时监护模块通过 WebSocket 接收实时音频流，并持续输出风险结果。

主要职责：

- 维护监护会话
- 接收流式音频数据
- 持续执行诈骗风险检测
- 向前端返回预警和风险信息

主要实现区域：

- `backend/app/main.py`
- `backend/app/routers/monitoring.py`
- `backend/app/services/fraud_detection.py`

### 3. 案例分析模块

案例分析模块用于对上传的音频或文件做离线诈骗风险分析。

主要职责：

- 接收上传文件
- 触发分析任务
- 返回分析进度和分析结果

主要实现区域：

- `backend/app/routers/analysis.py`

## 开发说明

### 环境假设

当前仓库强依赖 `fraud_detection` 这个 conda 环境。

这个环境提供了：

- Python 运行时
- Node.js
- npm
- 后端模型和音频相关依赖

常用激活命令：

```bash
conda activate fraud_detection
```

如果当前 shell 还没有初始化 conda：

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate fraud_detection
```

### 推荐启动方式

当前推荐使用一键启动脚本：

```bash
cd /root/autodl-tmp/fraud-blocking-system
bash start.sh
```

当前 `start.sh` 的行为是：

- 从当前环境中检测 Python、Node、npm
- 检查后端关键依赖
- 如果前端缺少 `node_modules`，自动安装依赖
- 先启动后端
- 再启动前端
- 如果检测到 `cloudflared`，自动启动 Cloudflare Quick Tunnel
- 等待后端和前端健康检查通过
- 打印本地地址、日志路径和公网地址
- 通过内部 `nohup` 保持服务在后台运行，然后脚本退出

这套流程是为了适配远程 SSH 开发场景。启动完成后，即使断开 SSH，服务也会继续运行。

### 停止方式

停止命令：

```bash
cd /root/autodl-tmp/fraud-blocking-system
bash stop.sh
```

`stop.sh` 会尝试停止：

- 后端 Uvicorn 进程
- 前端 Vite 开发服务器
- Cloudflare 隧道进程

### 日志位置

常用日志文件：

- 后端日志：`backend/logs/dev-backend.log`
- 前端日志：`frontend/.logs/dev-frontend.log`
- Tunnel 日志：`frontend/.logs/cloudflared-quick-tunnel.log`

常用查看命令：

```bash
tail -f backend/logs/dev-backend.log
tail -f frontend/.logs/dev-frontend.log
tail -f frontend/.logs/cloudflared-quick-tunnel.log
```

### 手动开发模式

如果需要手动分开启动前后端，也可以使用下面的方式。

后端：

```bash
cd /root/autodl-tmp/fraud-blocking-system/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：

```bash
cd /root/autodl-tmp/fraud-blocking-system/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

## 开发约束与注意事项

### 严格模式

当前仓库默认启用严格模式：

- `STRICT_NO_FALLBACK=true`

它的实际含义是：

- 如果模型或音频关键依赖缺失，应该明确报错
- 监护和分析模块不应该静默降级为假结果或零结果

这点在调试时非常重要，因为页面能打开，不代表模型链路就真的可用。

### 远程开发特点

这个仓库明显是按远程 Linux 或 AutoDL 这类环境去设计的。

主要体现为：

- 仅有本地 `127.0.0.1` 地址并不够，需要远程访问方案
- Cloudflare Quick Tunnel 被纳入了正式开发流程
- 对外暴露时通常以前端开发服务器为入口

### 构建与质量工具

前端常用脚本：

```bash
npm run dev
npm run build
npm run preview
npm run lint
npm run format
```

后端依赖中已经包含：

- pytest
- pytest-asyncio
- black
- isort

仓库当前还提供了一个 smoke test 入口：

```bash
/root/autodl-tmp/fraud_detection/bin/python scripts/smoke_test.py
```

## 实用文件导航

如果要快速熟悉项目，最重要的文件是：

- `README.md`：项目整体使用说明
- `README_STARTUP.md`：启动和远程访问说明
- `start.sh`：一键启动脚本
- `stop.sh`：停止脚本
- `backend/app/main.py`：后端主入口
- `backend/app/services/ai_chat.py`：AI 陪练核心逻辑
- `backend/app/services/fraud_detection.py`：实时监护核心逻辑
- `frontend/src/pages/PracticePage.vue`：陪练页面
- `frontend/src/pages/MonitorPage.vue`：实时监护页面
- `frontend/src/pages/AnalysisPage.vue`：案例分析页面

## 面向智能体的快速上下文

如果这份仓库要给 VS Code 智能体或其他 AI 助手使用，最重要的上下文是：

- 这是一个 Vue 3 + FastAPI 的前后端分离项目，不是 Next.js，也不是单体应用
- 启动流程默认假设 `fraud_detection` conda 环境已经激活
- 后端开发不只是 Web API，还强依赖模型、音频和语音处理依赖
- 远程开发是第一优先场景，Cloudflare 隧道支持是正式能力
- `/practice`、`/monitor`、`/analysis` 是三条核心业务链路
- `start.sh` 是推荐入口，但手动分开启动前后端也仍然可行

## 适用场景

这份文档适合用于：

- 新成员上手资料
- 技术方案或架构梳理
- VS Code 智能体上下文说明
- 在深入读代码前的快速项目总览