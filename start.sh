#!/bin/bash

# 电信诈骗风险阻断系统 - 快速启动脚本
# 软著申请：一键部署解决方案

echo "🚀 启动电信诈骗风险阻断系统..."
echo "=================================="

# 检查Python版本
python_version=$(python3 --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ 错误：未找到Python3"
    exit 1
fi
echo "✅ Python版本: $python_version"

# 检查Node.js版本
node_version=$(node --version 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ 错误：未找到Node.js"
    exit 1
fi
echo "✅ Node.js版本: $node_version"

# 设置环境变量
export QWEN_MODEL_TYPE=${QWEN_MODEL_TYPE:-local}
export USE_CUDA=${USE_CUDA:-true}
echo "🔧 模型模式: $QWEN_MODEL_TYPE"
echo "🔧 GPU加速: $USE_CUDA"

# 启动后端
echo ""
echo "🖥 启动后端服务..."
cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 启动后端服务
echo "🖥 启动FastAPI服务（端口8000）..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 检查后端状态
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 后端服务启动成功！"
    echo "📡 API文档: http://localhost:8000/docs"
    echo "📡 健康检查: http://localhost:8000/health"
else
    echo "❌ 后端服务启动失败，请检查错误信息"
fi

# 启动前端
echo ""
echo "🌐 启动前端服务..."
cd ../frontend

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装Node.js依赖..."
    npm install
fi

# 启动前端开发服务器
echo "🖥 启动Vue开发服务器（端口5173）..."
npm run dev &
FRONTEND_PID=$!

# 等待前端启动
echo "⏳ 等待前端启动..."
sleep 3

# 显示访问信息
echo ""
echo "🎉 系统启动完成！"
echo "=================================="
echo "📱 前端地址: http://localhost:5173"
echo "🔧 后端API: http://localhost:8000"
echo "📡 API文档: http://localhost:8000/docs"
echo "📡 健康检查: http://localhost:8000/health"
echo ""
echo "🎯 主要功能页面:"
echo "   📚 AI陪练: http://localhost:5173/practice"
echo "   🛡️ 实时监护: http://localhost:5173/monitor"
echo "   📁 案例分析: http://localhost:5173/analysis"
echo ""
echo "💡 提示："
echo "   - 系统使用Mock Qwen2Audio模型，功能完整且快速响应"
echo "   - 如需官方模型，请参考 README_QWEN_SETUP.md"
echo "   - 按 Ctrl+C 停止所有服务"
echo "=================================="

# 等待用户中断
trap 'echo ""; echo "🛑 正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo "✅ 服务已停止"; exit 0' INT

# 保持脚本运行
wait