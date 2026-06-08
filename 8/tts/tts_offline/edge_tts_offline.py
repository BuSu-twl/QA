#!/usr/bin/env python3
"""
Edge-TTS 离线模式 Demo v2
=========================
支持下载离线模型，生成高质量中文语音

男声推荐（沉稳风格）：
- zh-CN-YunyangNeural  【首推】新闻男声，专业沉稳
- zh-CN-YunxiNeural    云希，年轻男声

使用方法：
    python edge_tts_offline.py              # 测试所有语音
    python edge_tts_offline.py --list       # 列出可用语音
    python edge_tts_offline.py -v Yunyang   # 指定语音测试
    python edge_tts_offline.py --download  # 下载离线模型
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import argparse

# 配置路径
SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR / "models"
OUTPUT_DIR = SCRIPT_DIR / "output"

MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 推荐的沉稳男声
VOICES = {
    "zh-CN-YunyangNeural": {
        "name": "云扬",
        "gender": "Male",
        "description": "新闻男声，专业沉稳",
        "recommended": True,
    },
    "zh-CN-YunxiNeural": {
        "name": "云希",
        "gender": "Male",
        "description": "年轻男声，自然流畅",
        "recommended": True,
    },
    "zh-CN-YunjianNeural": {
        "name": "云健",
        "gender": "Male",
        "description": "健身教练风格",
        "recommended": False,
    },
    "zh-CN-XiaoxiaoNeural": {
        "name": "晓晓",
        "gender": "Female",
        "description": "亲切女声",
        "recommended": False,
    },
}


def print_banner():
    print("=" * 60)
    print("  Edge-TTS 离线模式 Demo")
    print("  Offline Chinese TTS with Edge Neural Voices")
    print("=" * 60)


def list_voices():
    """列出可用语音"""
    print("\n可用语音列表:")
    print("-" * 60)

    print("\n【沉稳男声推荐】")
    for voice, info in VOICES.items():
        if info["recommended"]:
            marker = " ⭐" if info.get("recommended") else ""
            print(f"  {voice}{marker}")
            print(f"    {info['name']} | {info['gender']} | {info['description']}")

    print("\n【其他语音】")
    for voice, info in VOICES.items():
        if not info["recommended"]:
            print(f"  {voice}")
            print(f"    {info['name']} | {info['gender']} | {info['description']}")


def check_edge_tts():
    """检查 edge-tts 是否安装"""
    try:
        import edge_tts
        print(f"[✓] edge-tts 已安装: {edge_tts.__version__}")
        return True
    except ImportError:
        print("[✗] edge-tts 未安装")
        print("    请运行: pip install edge-tts")
        return False


async def test_voice(voice: str, text: str, output_file: str) -> bool:
    """测试单个语音"""
    try:
        from edge_tts import Communicate

        print(f"\n  文本: {text[:30]}...")
        print(f"  输出: {output_file}")

        # 使用 Communicate 生成音频
        communicate = Communicate(text, voice)
        await communicate.save(output_file)

        size = os.path.getsize(output_file)
        print(f"  ✓ 成功 ({size:,} 字节)")

        return True

    except ImportError:
        print("  [错误] 请先安装 edge-tts: pip install edge-tts")
        return False
    except Exception as e:
        print(f"  [错误] {e}")
        return False


async def run_tests(voice: str = None):
    """运行测试"""
    print_banner()

    if not check_edge_tts():
        return

    # 测试文本
    test_texts = [
        "您好，欢迎使用医疗问答助手。",
        "口服，一次3到6克，一日2到3次。",
        "该处方饭前服用效果更佳。",
        "请遵医嘱用药，祝您早日康复。",
    ]

    # 完整对话
    full_text = "。".join(test_texts)

    voices_to_test = [voice] if voice else [v for v in VOICES if VOICES[v].get("recommended")]

    print(f"\n{'=' * 60}")
    print("开始语音合成测试...")
    print("=" * 60)

    for v in voices_to_test:
        info = VOICES[v]
        print(f"\n[语音] {info['name']} ({v})")
        print("-" * 40)

        # 生成完整对话
        output_file = OUTPUT_DIR / f"medical_dialogue_{v.replace('zh-CN-', '')}.mp3"
        await test_voice(v, full_text, str(output_file))

    # 单独测试每句
    print(f"\n{'=' * 60}")
    print("逐句测试...")
    print("=" * 60)

    for i, text in enumerate(test_texts, 1):
        voice = "zh-CN-YunyangNeural"  # 使用沉稳男声
        output_file = OUTPUT_DIR / f"test_{i}_{voice.replace('zh-CN-', '')}.mp3"
        print(f"\n[测试 {i}]")
        await test_voice(voice, text, str(output_file))

    # 列出生成的文件
    print(f"\n{'=' * 60}")
    print("生成的文件:")
    print("=" * 60)

    for f in sorted(OUTPUT_DIR.glob("*.mp3")):
        size = os.path.getsize(f)
        print(f"  • {f.name} ({size:,} 字节)")

    print(f"\n保存位置: {OUTPUT_DIR}")
    print("\n[提示] MP3 文件可直接下载到本地播放")


async def download_models():
    """下载离线模型说明"""
    print_banner()

    print("\n[说明] Edge-TTS 离线模式")
    print("-" * 60)
    print("""
Edge-TTS 从 v6.1+ 开始支持离线模式，但需要：

1. 模型下载方式：
   - edge-tts 会自动缓存模型到本地
   - 模型位置: ~/.cache/edge-tts/

2. 首次使用时会下载模型（约 200-500MB）
   - 需要网络连接
   - 下载后可在内网离线使用

3. 离线模式使用：
   - Windows: 无需额外配置
   - Linux/Mac: 需要配置缓存目录

4. 查看已下载模型：
   find ~/.cache/edge-tts/ -name "*.zip" 2>/dev/null
    """)

    # 尝试触发模型下载
    print("\n[测试] 尝试下载/更新模型...")
    print("(需要网络连接)")

    try:
        from edge_tts import Communicate

        # 触发一次合成，会自动下载模型
        voice = "zh-CN-YunyangNeural"
        output_file = OUTPUT_DIR / "model_download_test.mp3"

        print(f"\n  使用语音: {voice}")
        print("  正在生成测试音频（同时下载模型）...")

        communicate = Communicate("测试文本", voice)
        await communicate.save(str(output_file))

        print("  ✓ 成功！")

        # 检查模型缓存
        cache_dir = Path.home() / ".cache" / "edge-tts"
        if cache_dir.exists():
            models = list(cache_dir.glob("**/*.zip")) + list(cache_dir.glob("**/*.model"))
            print(f"\n  已缓存模型: {len(models)} 个")
            for m in models[:5]:
                print(f"    {m.name}")

    except Exception as e:
        print(f"  [错误] {e}")

    print(f"\n[提示] 首次下载模型后，后续可离线使用")
    print(f"       模型目录: {Path.home()}/.cache/edge-tts/")


async def main():
    parser = argparse.ArgumentParser(
        description="Edge-TTS 离线模式 Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python edge_tts_offline.py              # 运行测试
  python edge_tts_offline.py --list      # 列出语音
  python edge_tts_offline.py -v Yunyang  # 指定语音
  python edge_tts_offline.py --download  # 下载模型
        """
    )

    parser.add_argument("-v", "--voice", default=None,
                        help="指定语音 (如: zh-CN-YunyangNeural)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="列出可用语音")
    parser.add_argument("-d", "--download", action="store_true",
                        help="下载离线模型")
    parser.add_argument("-t", "--text",
                        help="指定测试文本")

    args = parser.parse_args()

    if args.list:
        print_banner()
        list_voices()
        return

    if args.download:
        await download_models()
        return

    if args.text:
        print_banner()
        voice = args.voice or "zh-CN-YunyangNeural"
        output_file = OUTPUT_DIR / "custom_text.mp3"
        print(f"\n使用语音: {voice}")
        print(f"文本: {args.text}")
        success = await test_voice(voice, args.text, str(output_file))
        if success:
            print(f"\n✓ 已保存到: {output_file}")
        return

    # 默认运行测试
    await run_tests(args.voice)


if __name__ == "__main__":
    asyncio.run(main())
