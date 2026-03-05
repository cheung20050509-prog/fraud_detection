#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen2Audio本地模型验证脚本
验证模型文件、配置和加载状态
"""
import os
import sys
from pathlib import Path

def main():
    """主验证函数"""
    print("=" * 60)
    print("Qwen2Audio本地模型验证工具")
    print("=" * 60)
    
    model_path = Path("./models/qwen2-audio")
    
    print("1. 检查模型目录")
    print(f"   目标路径: {model_path.absolute()}")
    
    if model_path.exists():
        print("   ✓ 模型目录存在")
        
        # 列出目录内容
        print("   目录内容:")
        try:
            for item in model_path.iterdir():
                print(f"     - {item.name}")
        except Exception as e:
            print(f"     错误: {e}")
    else:
        print("   ✗ 模型目录不存在")
        print("   请执行: mkdir -p models/qwen2-audio")
        return False
    
    print("\n2. 检查必需文件")
    required_files = ["config.json", "pytorch_model.bin", "tokenizer.json"]
    
    missing_files = []
    for file in required_files:
        file_path = model_path / file
        if file_path.exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (缺失)")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n   缺失文件: {', '.join(missing_files)}")
    
    print("\n3. 检查环境配置")
    env_vars = {
        "QWEN_MODEL_TYPE": os.getenv("QWEN_MODEL_TYPE"),
        "QWEN_LOCAL_MODEL_PATH": os.getenv("QWEN_LOCAL_MODEL_PATH"),
        "USE_CUDA": os.getenv("USE_CUDA")
    }
    
    for var, value in env_vars.items():
        if value:
            print(f"   ✓ {var} = {value}")
        else:
            print(f"   - {var} = 未设置")
    
    print("\n4. 检查Python依赖")
    packages = ["torch", "transformers", "numpy"]
    
    for package in packages:
        try:
            __import__(package)
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} (未安装)")
    
    print("\n" + "=" * 60)
    
    if not missing_files and model_path.exists():
        print("结果: 验证通过！")
        print("\n下一步:")
        print("1. 启动后端: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("2. 启动前端: cd ../frontend && npm run dev")
        print("3. 访问: http://localhost:5173")
        return True
    else:
        print("结果: 验证失败，请解决上述问题")
        print("\n建议:")
        print("1. 创建目录: mkdir -p models/qwen2-audio")
        print("2. 复制模型文件到 models/qwen2-audio/")
        print("3. 安装依赖: pip install torch transformers numpy")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)