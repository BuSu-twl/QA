#!/usr/bin/env python3
"""
Edge-TTS 离线音频生成测试 Demo
===============================
Edge-TTS 需要联网下载模型，但生成后可在其他设备离线播放

安装: pip install edge-tts
"""

import asyncio
import os
import sys

try:
    import edge_tts
except ImportError:
    print("正在安装 edge-tts...")
    os.system(f"{sys.executable} -m pip install edge-tts -q")
    import edge_tts


async def generate_audio(text: str, output_file: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bool:
    """
    生成音频文件

    Args:
        text: 要转换的文本
        output_file: 输出文件路径
        voice: 语音名称，默认使用晓晓（女声）

    Returns:
        bool: 是否成功
    """
    try:
        # 创建communicator
        communicate = edge_tts.Communicate(text, voice)

        # 生成音频文件
        await communicate.save(output_file)

        # 检查文件大小
        file_size = os.path.getsize(output_file)
        return True, file_size

    except Exception as e:
        return False, str(e)


async def list_voices():
    """列出可用的中文语音"""
    try:
        voices = await edge_tts.list_voices()
        chinese_voices = [v for v in voices if v["Locale"].startswith("zh-")]

        print("\n可用中文语音:")
        print("-" * 60)

        # 按性别分组
        female = [v for v in chinese_voices if v["Gender"] == "Female"]
        male = [v for v in chinese_voices if v["Gender"] == "Male"]

        print("\n【女声】")
        for v in female[:5]:
            print(f"  {v['ShortName']:35} - {v['FriendlyName']}")

        print("\n【男声】")
        for v in male[:5]:
            print(f"  {v['ShortName']:35} - {v['FriendlyName']}")

        return chinese_voices

    except Exception as e:
        print(f"获取语音列表失败: {e}")
        return []


async def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Edge-TTS 离线音频生成测试 Demo")
    print("=" * 60)

    # 1. 列出可用语音
    print("\n[1] 获取可用中文语音...")
    voices = await list_voices()

    # 选择测试语音（使用晓晓女声）
    test_voice = "zh-CN-XiaoxiaoNeural"
    print(f"\n[2] 使用语音: {test_voice}")

    # 3. 测试文本
    test_texts = [
        "您好，欢迎使用医疗问答助手。",
        "口服，一次3到6克，一日2到3次。",
        "该处方饭前服用效果更佳。",
        "请遵医嘱用药，祝您早日康复。"
    ]

    output_dir = "/workspace/projects/edge_tts_output"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[3] 开始生成音频...")
    print("-" * 60)

    all_success = True

    for i, text in enumerate(test_texts, 1):
        output_file = os.path.join(output_dir, f"test_{i}.mp3")

        print(f"\n测试 {i}: {text}")
        print(f"  输出文件: {output_file}")

        success, result = await generate_audio(text, output_file, test_voice)

        if success:
            print(f"  ✓ 生成成功！文件大小: {result:,} 字节")
        else:
            print(f"  ✗ 生成失败: {result}")
            all_success = False

    # 4. 生成组合音频
    print("\n" + "=" * 60)
    print("[4] 生成完整对话音频...")

    combined_text = "。".join(test_texts) + "。"
    combined_file = os.path.join(output_dir, "complete_dialogue.mp3")

    success, result = await generate_audio(combined_text, combined_file, test_voice)

    if success:
        print(f"  ✓ 生成成功！文件: {combined_file}")
        print(f"    文件大小: {result:,} 字节")
    else:
        print(f"  ✗ 生成失败: {result}")
        all_success = False

    # 5. 总结
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    if all_success:
        print("\n所有音频文件已生成:")
        for f in os.listdir(output_dir):
            fpath = os.path.join(output_dir, f)
            size = os.path.getsize(fpath)
            print(f"  • {f} ({size:,} 字节)")

        print("\n提示:")
        print("  1. MP3 文件可下载到本地播放")
        print("  2. 如需集成到项目，可转换为 base64 或 WAV 格式")
        print("  3. Edge-TTS 需要联网首次下载模型，之后可离线使用")
    else:
        print("\n部分测试失败，请检查网络连接和 edge-tts 安装")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Edge-TTS 离线音频生成测试 Demo")
    print("=" * 60)

    # 检查安装
    try:
        import edge_tts
        print("\n✓ edge-tts 已安装")
    except ImportError:
        print("\n正在安装 edge-tts...")
        os.system(f"{sys.executable} -m pip install edge-tts")
        print("✓ edge-tts 安装完成")

    # 运行异步测试
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()
