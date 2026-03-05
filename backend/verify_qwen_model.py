#!/usr/bin/env python3
"""
Qwen2Audio本地模型验证脚本
验证模型文件、配置和加载状态
"""
import os
import sys
from pathlib import Path

def verify_model_structure():
    """验证模型目录结构"""
    print("验证Qwen2Audio模型结构...")
    
    model_path = Path("./models/qwen2-audio")
    
    print(f"检查模型目录: {model_path.absolute()}")
    
    if not model_path.exists():
        print("❌ 模型目录不存在")
        print("📝 请创建目录:")
        print(f"   mkdir -p {model_path}")
        return False
    
    print("✅ 模型目录存在")
    
    # 检查必需文件
    required_files = [
        "config.json",
        "tokenizer.json"
    ]
    
    optional_files = [
        "pytorch_model.bin",
        "pytorch_model.bin.index.json",
        "model.safetensors",
        "model.safetensors.index.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "preprocessor_config.json",
        "vocab.json"
    ]
    
    missing_required = []
    found_optional = []
    
    for file in required_files:
        if (model_path / file).exists():
            print(f"✅ 必需文件: {file}")
        else:
            missing_required.append(file)
            print(f"❌ 缺失必需文件: {file}")
    
    for file in optional_files:
        if (model_path / file).exists():
            found_optional.append(file)
            print(f"✅ 可选文件: {file}")
    
    if missing_required:
        print(f"\n🚨 缺失必需文件: {missing_required}")
        return False
    
    print(f"\n📊 找到 {len(found_optional)} 个可选文件")
    return True

def verify_config():
    """验证配置文件"""
    print("\n🔧 验证系统配置...")
    
    # 检查环境变量
    model_type = os.getenv("QWEN_MODEL_TYPE")
    model_path = os.getenv("QWEN_LOCAL_MODEL_PATH")
    
    print(f"🔧 QWEN_MODEL_TYPE: {model_type or '未设置'}")
    print(f"🔧 QWEN_LOCAL_MODEL_PATH: {model_path or '未设置'}")
    
    # 检查配置文件
    config_path = Path("app/config.py")
    if config_path.exists():
        print("✅ 配置文件存在: config.py")
        
        # 读取配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'qwen_model_path' in content:
                    print("✅ 模型路径配置存在")
                else:
                    print("❌ 模型路径配置缺失")
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
    else:
        print("❌ 配置文件不存在: config.py")
    
    return True

def verify_dependencies():
    """验证Python依赖"""
    print("\n📦 验证依赖包...")
    
    required_packages = [
        "torch",
        "transformers",
        "numpy"
    ]
    
    optional_packages = [
        "accelerate",
        "safetensors",
        "soundfile",
        "librosa"
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ 必需包: {package}")
        except ImportError:
            missing_required.append(package)
            print(f"❌ 缺失必需包: {package}")
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ 可选包: {package}")
        except ImportError:
            missing_optional.append(package)
            print(f"⚠️ 缺失可选包: {package}")
    
    if missing_required:
        print(f"\n🚨 请安装缺失的必需包:")
        print(f"   pip install {' '.join(missing_required)}")
    
    if missing_optional:
        print(f"\n💡 建议安装的可选包:")
        print(f"   pip install {' '.join(missing_optional)}")
    
    return len(missing_required) == 0

def verify_model_loading():
    """验证模型加载"""
    print("\n🚀 验证模型加载...")
    
    try:
        # 添加app目录到路径
        sys.path.append(str(Path(__file__).parent / "app"))
        
        from ml_models.qwen_integration import QwenAudioProcessor
        
        # 创建处理器
        processor = QwenAudioProcessor()
        
        print("✅ QwenAudioProcessor 初始化成功")
        
        # 测试基本功能
        test_result = processor.process_audio("test", mode="fraud_detection")
        if test_result and "risk_score" in test_result:
            print("✅ 基本功能测试通过")
            print(f"📊 测试结果: 风险分数 = {test_result['risk_score']}")
        else:
            print("⚠️ 基本功能测试失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return False

def generate_report(results):
    """生成验证报告"""
    print("\n" + "="*60)
    print("📋 验证报告")
    print("="*40)
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有验证通过！您的Qwen2Audio模型已准备就绪。")
        print("\n🚀 下一步:")
        print("   1. 启动后端: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("   2. 启动前端: cd ../frontend && npm run dev")
        print("   3. 访问系统: http://localhost:5173")
    else:
        print("\n🚨 验证未完全通过，请解决上述问题。")
        print("\n🔧 常见解决方案:")
        print("   • 模型文件缺失 -> 复制微调模型到 ./models/qwen2-audio/")
        print("   • 依赖包缺失 -> pip install -r requirements.txt")
        print("   • 配置错误 -> 检查 .env 文件或环境变量")

def main():
    """主验证函数"""
    print("Qwen2Audio本地模型验证工具")
    print("="*60)
    
    results = {}
    
    # 执行各项验证
    results["model_structure"] = verify_model_structure()
    results["config"] = verify_config()
    results["dependencies"] = verify_dependencies()
    results["model_loading"] = verify_model_loading()
    
    # 生成报告
    generate_report(results)
    
    # 返回验证结果
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)