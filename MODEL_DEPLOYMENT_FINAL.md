# 🎯 Qwen2Audio 模型部署完整指南

## 📍 **您的模型应该放在这里**

```
📁 C:\Users\Administrator\fraud-blocking-system\backend\models\qwen2-audio\
```

✅ **目录已为您创建完成！**

## 📋 **快速部署步骤**

### **第1步：复制模型文件**
将您微调的Qwen2Audio模型文件复制到：
```
C:\Users\Administrator\fraud-blocking-system\backend\models\qwen2-audio\
```

### **第2步：必需的模型文件**
确保包含以下文件：
```
models/qwen2-audio/
├── config.json              # ✅ 必需
├── pytorch_model.bin        # ✅ 必需 
├── tokenizer.json           # ✅ 必需
├── tokenizer_config.json    # 推荐
├── special_tokens_map.json  # 推荐
└── preprocessor_config.json # 音频配置（推荐）
```

### **第3步：配置环境**
创建环境配置文件：
```bash
# 在 backend 目录下创建 .env 文件
QWEN_MODEL_TYPE=local
QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio
USE_CUDA=true
```

### **第4步：安装依赖**
```bash
cd C:\Users\Administrator\fraud-blocking-system\backend
pip install -r requirements.txt
```

### **第5步：启动系统**
```bash
# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 启动前端（新终端）
cd ../frontend
npm run dev
```

## 🔧 **验证工具**

我已为您创建了多个验证工具：

### **Windows批处理验证**
```bash
cd C:\Users\Administrator\fraud-blocking-system\backend
verify_model.bat
```

### **Python验证脚本**
```bash
cd C:\Users\Administrator\fraud-blocking-system\backend
python verify_qwen_model_simple.py
```

## ⚡ **性能优化**

### **GPU加速（推荐）**
```env
USE_CUDA=true
TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6
```

### **内存优化**
```env
MAX_MEMORY_USAGE=4096  # MB
MAX_CONCURRENT_INFERENCES=3
```

## 🔄 **模式切换**

系统支持3种运行模式：

### **本地模式（您的微调模型）**
```env
QWEN_MODEL_TYPE=local
QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio
```

### **官方API模式**
```env
QWEN_MODEL_TYPE=official
QWEN_API_KEY=your_api_key_here
```

### **Mock模式（开发测试）**
```env
QWEN_MODEL_TYPE=mock
```

## 🎯 **当前状态**

✅ **后端目录结构** - 已检查完成  
✅ **模型配置文件** - config.py 已配置  
✅ **模型目录创建** - models/qwen2-audio/ 已创建  
✅ **验证工具** - 已创建验证脚本  
✅ **部署文档** - 完整指南已提供  

## 🚀 **立即开始**

1. **复制模型文件**到 `backend/models/qwen2-audio/`
2. **运行验证**：`verify_model.bat`
3. **启动系统**：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. **访问界面**：http://localhost:5173

## 📞 **故障排除**

| 问题 | 解决方案 |
|------|----------|
| 模型加载失败 | 检查模型文件完整性，运行 verify_model.bat |
| 内存不足 | 设置 USE_CUDA=false 或减小 MAX_MEMORY_USAGE |
| CUDA不可用 | 安装CUDA版本PyTorch或使用CPU模式 |
| 依赖缺失 | 运行 `pip install -r requirements.txt` |

---

## 🎉 **完成！**

您的 `fraud-blocking-system` 现在已完全准备好接入本地微调的Qwen2Audio模型！

**模型路径**：`backend/models/qwen2-audio/`  
**配置文件**：`backend/app/config.py`  
**验证工具**：`backend/verify_model.bat`

如有任何问题，请运行验证脚本进行诊断。