"""
Edge-TTS 模型下载脚本
自动下载语音模型并预生成音频文件到 models 目录
"""
import os
import sys
import asyncio

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')

# 创建目录
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


def download_models():
    """下载并缓存语音到本地目录"""
    # 需要下载的语音列表
    voices = [
        'zh-CN-YunyangNeural',   # 云扬 - 男声（医疗推荐）
        'zh-CN-XiaoxiaoNeural',   # 晓晓 - 女声
    ]

    # 预生成的测试音频（用于验证模型可用性）
    test_texts = [
        "您好，欢迎使用医疗问答助手。",
        "口服，一次3到6克，一日2到3次。",
        "请遵医嘱用药，祝您早日康复。"
    ]

    async def download_voice(voice_name: str):
        """下载并缓存单个语音"""
        print(f"正在处理 {voice_name}...")

        try:
            import edge_tts

            # 触发模型下载并生成测试音频
            for i, text in enumerate(test_texts):
                tts = edge_tts.Communicate(text, voice_name)
                audio_chunks = []

                async for chunk in tts.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])

                # 保存到 audio 目录
                audio_data = b"".join(audio_chunks)
                filename = f"{voice_name}_test_{i+1}.mp3"
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(audio_data)
                print(f"  ✓ 保存: {filename} ({len(audio_data)/1024:.1f}KB)")

            print(f"✓ {voice_name} 处理完成")
            return True

        except Exception as e:
            print(f"✗ {voice_name} 处理失败: {e}")
            return False

    async def main():
        """主函数"""
        print("=" * 50)
        print("Edge-TTS 模型下载工具")
        print("=" * 50)
        print(f"下载目录: {MODELS_DIR}")
        print(f"语音数量: {len(voices)}")
        print("=" * 50)
        print()

        # 检查 edge-tts 是否安装
        try:
            import edge_tts
            print(f"✓ edge-tts 已安装 (版本: {edge_tts.__version__})")
            print()
        except ImportError:
            print("✗ edge-tts 未安装，正在安装...")
            os.system(f"{sys.executable} -m pip install edge-tts")
            try:
                import edge_tts
                print(f"✓ edge-tts 安装成功")
            except:
                print("✗ edge-tts 安装失败")
                return

        print("开始下载模型...")
        print("-" * 50)

        success_count = 0
        for voice in voices:
            if await download_voice(voice):
                success_count += 1
            print()

        print("-" * 50)
        print(f"下载完成: {success_count}/{len(voices)} 成功")

        if success_count > 0:
            print()
            print("=" * 50)
            print(f"✓ 音频文件已保存到: {AUDIO_DIR}")
            print("=" * 50)
            print()
            print("下一步：")
            print("1. 在内网电脑上运行: python app.py")
            print("2. 首次运行会报错（无法联网），这是正常的")

    asyncio.run(main())


if __name__ == '__main__':
    download_models()
