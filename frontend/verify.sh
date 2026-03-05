#!/bin/bash

echo "🔍 验证欺诈阻断系统前端页面..."

# 检查所有必需的页面文件是否存在
pages=(
    "src/pages/HomePage.vue"
    "src/pages/PracticePage.vue" 
    "src/pages/MonitorPage.vue"
    "src/pages/AnalysisPage.vue"
    "src/pages/SettingsPage.vue"
    "src/pages/NotFoundPage.vue"
)

echo "📄 检查页面文件..."
for page in "${pages[@]}"; do
    if [ -f "$page" ]; then
        echo "✅ $page - 存在"
    else
        echo "❌ $page - 缺失"
        exit 1
    fi
done

# 检查配置文件
configs=(
    "src/router/index.ts"
    "src/main.ts"
    "src/App.vue"
    "package.json"
    "tsconfig.json"
    "vite.config.ts"
    "tailwind.config.js"
    "postcss.config.js"
)

echo "📋 检查配置文件..."
for config in "${configs[@]}"; do
    if [ -f "$config" ]; then
        echo "✅ $config - 存在"
    else
        echo "❌ $config - 缺失"
        exit 1
    fi
done

# 检查工具文件
utils=(
    "src/utils/Recorder.ts"
)

echo "🛠️ 检查工具文件..."
for util in "${utils[@]}"; do
    if [ -f "$util" ]; then
        echo "✅ $util - 存在"
    else
        echo "❌ $util - 缺失"
        exit 1
    fi
done

# 检查依赖是否安装
if [ -d "node_modules" ]; then
    echo "✅ node_modules - 存在"
else
    echo "❌ node_modules - 缺失，请运行 npm install"
    exit 1
fi

# 检查构建产物
echo "🏗️ 检查构建..."
if npm run build > /dev/null 2>&1; then
    echo "✅ 构建成功"
    if [ -d "dist" ]; then
        echo "✅ dist 目录 - 存在"
    else
        echo "❌ dist 目录 - 缺失"
        exit 1
    fi
else
    echo "❌ 构建失败"
    exit 1
fi

echo "🎉 所有检查通过！前端系统已准备就绪。"
echo ""
echo "🚀 启动命令："
echo "   开发环境: npm run dev"
echo "   生产构建: npm run build"
echo "   预览构建: npm run preview"
echo ""
echo "🌐 访问地址："
echo "   本地: http://localhost:5173"
echo "   网络: http://192.168.146.1:5173"