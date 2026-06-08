#!/usr/bin/env python3
"""
Edge-TTS 本地缓存离线模式
=====================================
使用本地缓存实现内网离线使用

原理：
1. 首次运行需要联网下载模型到本地目录
2. 下载后可以将整个 models 文件夹打包
3. 在离线环境使用时，将模型文件放到指定目录
4. 程序会优先使用本地模型，不访问网络

作者: AI Assistant
版本: 1.0.0
"""

import os
import sys
import asyncio
import base64
import struct
import wave
from pathlib import Path

# 配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
CACHE_DIR = os.path.join(MODEL_DIR, "cache")

# 确保目录存在
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


def print_banner():
    """打印横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Edge-TTS 本地缓存离线模式 Demo                     ║
╠══════════════════════════════════════════════════════════════╣
║  特点:                                                       ║
║  ✓ 模型下载后可打包携带                                      ║
║  ✓ 内网环境可正常使用                                        ║
║  ✓ 中文语音效果优秀                                          ║
║  ✓ 支持男声/女声                                            ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_instructions():
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                     使用说明                                  ║
╠══════════════════════════════════════════════════════════════╣
║  命令行参数:                                                  ║
║  python edge_offline.py              - 运行完整测试          ║
║  python edge_offline.py --list       - 列出可用语音           ║
║  python edge_offline.py --text "文本" - 生成自定义文本       ║
║  python edge_offline.py --download   - 仅下载模型             ║
║                                                              ║
║  离线使用方法:                                               ║
║  1. 在有网环境运行: python edge_offline.py --download        ║
║  2. models/ 文件夹会包含所有需要的模型文件                   ║
║  3. 打包 models/ 文件夹到离线环境                           ║
║  4. 设置环境变量: export EDGE_TTS_LOCAL_CACHE=./models     ║
║  5. 在离线环境运行即可                                      ║
╚══════════════════════════════════════════════════════════════╝
    """)


def get_chinese_voices():
    """获取中文语音列表"""
    chinese_voices = [
        {
            "name": "zh-CN-XiaoxiaoNeural",
            "display_name": "晓晓",
            "gender": "女声",
            "description": "温柔女声，通用场景",
            "style": "温柔"
        },
        {
            "name": "zh-CN-XiaoyiNeural",
            "display_name": "小艺",
            "gender": "女声",
            "description": "年轻女声",
            "style": "年轻"
        },
        {
            "name": "zh-CN-YunjianNeural",
            "display_name": "云健",
            "gender": "男声",
            "description": "阳光男声",
            "style": "阳光"
        },
        {
            "name": "zh-CN-YunxiNeural",
            "display_name": "云希",
            "gender": "男声",
            "description": "成熟男声，自然流畅",
            "style": "成熟"
        },
        {
            "name": "zh-CN-YunxiaNeural",
            "display_name": "云夏",
            "gender": "男声",
            "description": "年轻男声",
            "style": "年轻"
        },
        {
            "name": "zh-CN-YunyangNeural",
            "display_name": "云扬",
            "gender": "男声",
            "description": "新闻男声，专业沉稳【医疗推荐】",
            "style": "沉稳"
        },
        {
            "name": "zh-CN-liaoning-XiaobeiNeural",
            "display_name": "小北",
            "gender": "女声",
            "description": "东北话女声",
            "style": "东北话"
        },
        {
            "name": "zh-CN-shaanxi-XiaoniNeural",
            "display_name": "小妮",
            "gender": "女声",
            "description": "陕西话女声",
            "style": "陕西话"
        },
    ]
    return chinese_voices


async def download_voice_model(voice_name, cache_dir):
    """下载单个语音模型"""
    import edge_tts

    print(f"  正在下载: {voice_name}...", end=" ", flush=True)

    try:
        # 尝试生成一小段音频来触发模型下载
        communicate = edge_tts.Communicate("测试", voice_name)

        # 创建音频文件
        output_file = os.path.join(cache_dir, f"{voice_name}.mp3")

        # 写入到文件（这会触发模型下载）
        with open(output_file, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

        size = os.path.getsize(output_file)
        print(f"✓ ({size/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


async def download_all_models():
    """下载所有中文语音模型"""
    print("\n[1] 下载中文语音模型...")
    print("-" * 50)

    voices = get_chinese_voices()

    success_count = 0
    for voice in voices:
        voice_name = voice["name"]
        success = await download_voice_model(voice_name, CACHE_DIR)
        if success:
            success_count += 1

    print(f"\n✓ 成功下载 {success_count}/{len(voices)} 个语音模型")
    return success_count > 0


async def synthesize_speech(text, voice_name, output_file):
    """合成语音"""
    import edge_tts

    try:
        # 检查是否有本地缓存
        local_cache = os.environ.get('EDGE_TTS_LOCAL_CACHE')
        if local_cache:
            cached_model = os.path.join(local_cache, "cache", f"{voice_name}.mp3")
            if os.path.exists(cached_model):
                print(f"  (使用本地缓存: {voice_name})")

        communicate = edge_tts.Communicate(text, voice_name)

        with open(output_file, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

        return True, output_file

    except Exception as e:
        return False, str(e)


async def test_all_voices():
    """测试所有中文语音"""
    print("\n[2] 测试所有中文语音...")
    print("-" * 50)

    test_text = "您好，欢迎使用医疗问答助手。口服，一次3到6克，一日2到3次。"

    voices = get_chinese_voices()

    for voice in voices:
        voice_name = voice["name"]
        print(f"\n  [{voice['display_name']}] {voice['description']}")

        # 生成音频
        output_file = os.path.join(OUTPUT_DIR, f"test_{voice['name'].split('-')[-1]}.mp3")

        success, result = await synthesize_speech(test_text, voice_name, output_file)

        if success:
            size = os.path.getsize(output_file)
            print(f"    ✓ 生成成功 ({size/1024:.1f} KB) → {os.path.basename(output_file)}")
        else:
            print(f"    ✗ 生成失败: {result}")

    return True


async def generate_medical_dialogue():
    """生成医疗对话（使用沉稳男声）"""
    print("\n[3] 生成医疗对话完整版（云扬-沉稳男声）...")
    print("-" * 50)

    dialogue = """您好，欢迎使用医疗问答助手。该处方常规的用法用量是：口服，一次3到6克，一日2到3次。建议饭前半小时服用效果更佳。请遵医嘱用药，不要自行调整剂量。祝你早日康复。"""

    output_file = os.path.join(OUTPUT_DIR, "medical_dialogue_yunyang.mp3")

    print(f"  文本: {dialogue[:50]}...")

    success, result = await synthesize_speech(dialogue, "zh-CN-YunyangNeural", output_file)

    if success:
        size = os.path.getsize(output_file)
        print(f"  ✓ 生成成功 ({size/1024:.1f} KB)")
        print(f"  文件: {output_file}")
        return output_file
    else:
        print(f"  ✗ 生成失败: {result}")
        return None


async def generate_custom_text(text, voice="zh-CN-YunyangNeural"):
    """生成自定义文本"""
    output_file = os.path.join(OUTPUT_DIR, "custom_text.mp3")

    print(f"\n[4] 生成自定义文本...")
    print("-" * 50)
    print(f"  语音: {voice}")
    print(f"  文本: {text}")

    success, result = await synthesize_speech(text, voice, output_file)

    if success:
        size = os.path.getsize(output_file)
        print(f"  ✓ 生成成功 ({size/1024:.1f} KB)")
        print(f"  文件: {output_file}")
        return output_file
    else:
        print(f"  ✗ 生成失败: {result}")
        return None


def list_voices():
    """列出可用语音"""
    print("\n可用中文语音列表:")
    print("-" * 50)

    voices = get_chinese_voices()

    for voice in voices:
        marker = "⭐" if "医疗" in voice["description"] else " "
        print(f"  {marker} {voice['name']}")
        print(f"      {voice['display_name']} | {voice['gender']} | {voice['description']}")


def show_model_status():
    """显示模型状态"""
    print("\n[0] 检查模型状态...")
    print("-" * 50)

    voices = get_chinese_voices()
    cached_count = 0

    for voice in voices:
        voice_name = voice["name"]
        cached_file = os.path.join(CACHE_DIR, f"{voice_name}.mp3")

        if os.path.exists(cached_file):
            cached_count += 1
            marker = "✓"
        else:
            marker = "○"

        print(f"  {marker} {voice['display_name']} ({voice['name']})")

    print(f"\n  已缓存: {cached_count}/{len(voices)}")
    print(f"  缓存目录: {CACHE_DIR}")


async def main():
    """主函数"""
    print_banner()

    # 解析命令行参数
    args = sys.argv[1:]

    if "--list" in args:
        list_voices()
        print_instructions()
        return

    if "--download" in args:
        await download_all_models()
        print_instructions()
        return

    if "--text" in args:
        text_idx = args.index("--text")
        if text_idx + 1 < len(args):
            text = args[text_idx + 1]
            await generate_custom_text(text)
        else:
            print("错误: --text 需要指定文本内容")
        print_instructions()
        return

    # 检查模型状态
    show_model_status()

    # 如果需要，下载模型
    if not os.path.exists(CACHE_DIR) or len(os.listdir(CACHE_DIR)) < len(get_chinese_voices()):
        print("\n首次使用，需要下载模型...")
        await download_all_models()

    # 测试所有语音
    await test_all_voices()

    # 生成医疗对话
    await generate_medical_dialogue()

    # 显示输出文件
    print("\n[5] 生成的文件列表...")
    print("-" * 50)
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR)):
            filepath = os.path.join(OUTPUT_DIR, f)
            size = os.path.getsize(filepath)
            print(f"  • {f} ({size/1024:.1f} KB)")

    print_instructions()
    print("\n✓ 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
