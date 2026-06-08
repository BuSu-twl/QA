@echo off
REM TTS 离线服务启动脚本 (Windows)

echo ==========================================
echo 医疗问答助手 - TTS 离线服务
echo ==========================================

REM 检查依赖
echo 检查依赖...
python -c "import edge_tts" 2>nul
if errorlevel 1 (
    echo 安装依赖: edge-tts
    pip install edge-tts flask -q
)

REM 创建必要的目录
if not exist "temp_audio" mkdir "temp_audio"

REM 启动服务
echo.
echo 启动服务...
echo Web 界面: http://localhost:5001
echo API 文档: http://localhost:5001/health
echo.
echo 按 Ctrl+C 停止服务
echo ==========================================

python tts_server.py
