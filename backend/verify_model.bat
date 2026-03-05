@echo off
echo ============================================================
echo Qwen2Audio Model Verification
echo ============================================================
echo.

echo 1. Checking model directory
set MODEL_DIR=models\qwen2-audio
if exist "%MODEL_DIR%" (
    echo    OK: Model directory exists: %MODEL_DIR%
    echo    Directory contents:
    dir /b "%MODEL_DIR%"
) else (
    echo    ERROR: Model directory not found
    echo    Please create: %MODEL_DIR%
    echo    mkdir %MODEL_DIR%
)

echo.
echo 2. Checking required files
if exist "%MODEL_DIR%\config.json" (
    echo    OK: config.json
) else (
    echo    MISSING: config.json
)

if exist "%MODEL_DIR%\pytorch_model.bin" (
    echo    OK: pytorch_model.bin
) else (
    echo    MISSING: pytorch_model.bin
)

if exist "%MODEL_DIR%\tokenizer.json" (
    echo    OK: tokenizer.json
) else (
    echo    MISSING: tokenizer.json
)

echo.
echo 3. Environment variables
echo    QWEN_MODEL_TYPE: %QWEN_MODEL_TYPE%
echo    QWEN_LOCAL_MODEL_PATH: %QWEN_LOCAL_MODEL_PATH%
echo    USE_CUDA: %USE_CUDA%

echo.
echo 4. Configuration file
if exist "app\config.py" (
    echo    OK: config.py found
) else (
    echo    ERROR: config.py not found
)

echo.
echo ============================================================
echo Summary:
echo 1. If model directory doesn't exist:
echo    mkdir models
echo    mkdir models\qwen2-audio
echo.
echo 2. Copy your fine-tuned model files to:
echo    %CD%\%MODEL_DIR%\
echo.
echo 3. Required files:
echo    - config.json
echo    - pytorch_model.bin
echo    - tokenizer.json
echo.
echo 4. Set environment variables (optional):
echo    set QWEN_MODEL_TYPE=local
echo    set QWEN_LOCAL_MODEL_PATH=./models/qwen2-audio
echo.
echo 5. Start backend:
echo    uvicorn app.main:app --host 0.0.0.0 --port 8000
echo ============================================================

pause