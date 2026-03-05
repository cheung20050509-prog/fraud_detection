@echo off
chcp 65001 >nul
title 电信诈骗风险阻断系统 - 快速启动

echo.
echo 🚀 启动电信诈骗风险阻断系统...
echo ==================================

:: 检查Python版本
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到Python
    pause
    exit /b 1
)
echo ✅ Python版本检查通过

:: 检查Node.js版本  
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到Node.js
    pause
    exit /b 1
)
echo ✅ Node.js版本检查通过

:: 设置环境变量
if not defined QWEN_MODEL_TYPE (
    set QWEN_MODEL_TYPE=mock
)
if not defined USE_CUDA (
    set USE_CUDA=true
)
echo 🔧 模型模式: %QWEN_MODEL_TYPE%
echo 🔧 GPU加速: %USE_CUDA%

:: 启动后端
echo.
echo 🖥 启动后端服务...
cd backend

:: 检查虚拟环境
if not exist venv (
    echo 📦 创建Python虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate

:: 安装依赖
echo 📦 安装Python依赖...
pip install -r requirements.txt

:: 启动后端服务
echo 🖥 启动FastAPI服务（端口8000）...
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

:: 等待后端启动
echo ⏳ 等待后端启动...
timeout /t 5 /nobreak >nul

:: 检查后端状态
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 后端服务启动成功！
    echo 📡 API文档: http://localhost:8000/docs
    echo 📡 健康检查: http://localhost:8000/health
) else (
    echo ❌ 后端服务启动失败，请检查错误信息
)

:: 启动前端
echo.
echo 🌐 启动前端服务...
cd ..\frontend

:: 检查node_modules
if not exist node_modules (
    echo 📦 安装Node.js依赖...
    npm install
)

:: 启动前端开发服务器
echo 🖥 启动Vue开发服务器（端口5173）...
start /B npm run dev

:: 等待前端启动
echo ⏳ 等待前端启动...
timeout /t 3 /nobreak >nul

:: 显示访问信息
echo.
echo 🎉 系统启动完成！
echo ==================================
echo 📱 前端地址: http://localhost:5173
echo 🔧 后端API: http://localhost:8000
echo 📡 API文档: http://localhost:8000/docs
echo 📡 健康检查: http://localhost:8000/health
echo.
echo 🎯 主要功能页面:
echo    📚 AI陪练: http://localhost:5173/practice
echo    🛡️ 实时监护: http://localhost:5173/monitor
echo    📁 案例分析: http://localhost:5173/analysis
echo.
echo 💡 提示:
echo    - 系统使用Mock Qwen2Audio模型，功能完整且快速响应
echo    - 如需官方模型，请参考 README_QWEN_SETUP.md
echo    - 按 Ctrl+C 停止所有服务
echo ==================================

:: 保持窗口打开
pause