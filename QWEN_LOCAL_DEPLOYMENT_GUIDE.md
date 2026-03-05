# 🤖 Qwen2Audio 本地模型部署完整指南

## 📍 **模型存放位置**

根据检查结果，您微调的Qwen2Audio模型应该放在以下目录：

```
📁 C:\Users\Administrator\fraud-blocking-system\backend\models\qwen2-audio\
```

## 📁 **目录结构创建**

请创建以下目录结构来存放您的本地模型：

```bash
# 创建模型主目录
mkdir -p C:\Users\Administrator\fraud-blocking-system\backend\models\

# 创建Qwen2Audio专用目录
mkdir -p C:\Users\Administrator\fraud-blocking-system\backend\models\qwen2-audio\
```

## 🎯 **配置文件路径**

在 `backend/app/config.py` 中，模型路径配置为：

```python
qwen_model_path: str = "./models/qwen2-audio"
```

这是一个相对路径，指向 `backend/models/qwen2-audio/` 目录。

## 📋 **需要存放的模型文件**

请将您微调的Qwen2Audio模型文件放置在 `backend/models/qwen2-audio/` 目录下，通常包括：

### **必需文件**
```
backend/models/qwen2-audio/
├── config.json              # 模型配置文件
├── pytorch_model.bin        # PyTorch模型权重
├── tokenizer.json           # 分词器配置
├── tokenizer_config.json    # 分词器设置
├── special_tokens_map.json  # 特殊token映射
└── preprocessor_config.json # 音频预处理配置
```

### **可选文件**
```
backend/models/qwen2-audio/
├── vocab.json              # 词汇表
├── merges.txt             # BPE合并文件
├── added_tokens.json      # 添加的tokens
├── generation_config.json  # 生成配置
├── training_args.bin     # 训练参数
└── model.safetensors    # SafeTensor格式权重（如果使用）
```

## 🔧 **环境配置**

### **方法一：环境变量配置（推荐）**

```bash
# Windows (Command Prompt)
set QWEN_MODEL_TYPE=local
set QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio

# Windows (PowerShell)
$env:QWEN_MODEL_TYPE="local"
$env:QWEN_LOCAL_MODEL_PATH="./models/qwen2-audio"
```

### **方法二：创建.env文件**

在 `backend/` 目录下创建 `.env` 文件：

```env
# 模型配置
QWEN_MODEL_TYPE=local
QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio

# GPU设置
USE_CUDA=true
TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6

# 性能设置
MAX_MEMORY_USAGE=4096
MAX_CONCURRENT_INFERENCES=5
```

## 🚀 **启动流程**

### **1. 放置模型文件**
```bash
# 确保模型文件在正确位置
ls -la C:\Users\Administrator\fraud-blocking-system\backend\models\qwen2-audio\
```

### **2. 安装依赖**
```bash
cd C:\Users\Administrator\fraud-blocking-system\backend
pip install -r requirements.txt
```

### **3. 启动后端**
```bash
# 方法一：直接启动
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 方法二：使用环境变量
QWEN_MODEL_TYPE=local QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **4. 验证模型加载**
```bash
# 运行验证脚本
python verify_qwen_model.py
```

## 🎯 **快速验证脚本**

创建验证脚本检查模型是否正确加载：

```python
# save as: backend/verify_qwen_model.py
import os
import sys
from pathlib import Path

# 添加app目录到路径
sys.path.append(str(Path(__file__).parent / "app"))

def verify_model():
    """验证模型文件和配置"""
    
    # 检查模型路径
    model_path = Path("./models/qwen2-audio")
    
    if not model_path.exists():
        print("❌ 模型目录不存在")
        return False
    
    # 检查必需文件
    required_files = [
        "config.json",
        "pytorch_model.bin"
    ]
    
    missing_files = []
    for file in required_files:
        if not (model_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺失文件: {missing_files}")
        return False
    
    # 尝试加载模型
    try:
        from ml_models.qwen_integration import QwenAudioProcessor
        processor = QwenAudioProcessor(str(model_path))
        print("✅ 模型加载成功")
        return True
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return False

if __name__ == "__main__":
    success = verify_model()
    if success:
        print("🎉 模型验证通过！")
    else:
        print("🚨 模型验证失败，请检查配置")
```

## 🔄 **模型切换配置**

系统支持多种模型模式：

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

## ⚡ **性能优化建议**

### **GPU加速**
```env
USE_CUDA=true
TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6
```

### **内存管理**
```env
MAX_MEMORY_USAGE=4096  # MB
MAX_CONCURRENT_INFERENCES=3
```

### **模型量化**
如果模型过大，考虑使用量化：
```python
# 在模型加载时
model = AutoModel.from_pretrained(
    model_path,
    torch_dtype=torch.float16,  # 半精度
    device_map="auto"
)
```

## 🎯 **故障排除**

### **常见问题**

1. **模型文件不存在**
   - 确保路径正确：`backend/models/qwen2-audio/`
   - 检查文件权限

2. **内存不足**
   - 减少 `MAX_MEMORY_USAGE` 设置
   - 使用GPU而非CPU
   - 启用模型量化

3. **CUDA不可用**
   - 安装CUDA版本的PyTorch
   - 设置 `USE_CUDA=false` 使用CPU

4. **依赖缺失**
   - 安装transformers: `pip install transformers`
   - 安装torch: `pip install torch`

### **调试模式**
```bash
# 开启详细日志
export LOG_LEVEL=DEBUG
python backend/main.py
```

## 📋 **部署清单**

- [ ] 创建 `backend/models/qwen2-audio/` 目录
- [ ] 复制模型文件到目标目录
- [ ] 验证所有必需文件存在
- [ ] 配置环境变量或.env文件
- [ ] 安装Python依赖
- [ ] 启动后端服务
- [ ] 运行验证脚本
- [ ] 测试前端连接

---

🎉 **完成以上步骤后，您的本地微调Qwen2Audio模型就可以正常运行了！**

如有问题，请检查日志文件或运行验证脚本进行诊断。