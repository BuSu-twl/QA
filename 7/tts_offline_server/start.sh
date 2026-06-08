#!/bin/bash
# TTS 离线服务启动脚本

echo "=========================================="
echo "医疗问答助手 - TTS 离线服务"
echo "=========================================="

# 检查依赖
echo "检查依赖..."
python -c "import edge_tts" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖: edge-tts"
    pip install edge-tts flask -q
fi

# 创建必要的目录
mkdir -p temp_audio

# 启动服务
echo ""
echo "启动服务..."
echo "Web 界面: http://localhost:5001"
echo "API 文档: http://localhost:5001/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

python tts_server.py
