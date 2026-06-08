#!/usr/bin/env python3
"""
离线 TTS 测试 Demo
使用 Pyttsx3 实现本地语音合成
"""

import pyttsx3
import os


def get_chinese_voice(engine):
    """获取中文语音"""
    voices = engine.getProperty('voices')
    print(f"检测到 {len(voices)} 个语音：")

    # 优先查找中文语音
    for voice in voices:
        voice_name = voice.name.lower()
        voice_id = voice.id.lower()
        if any(keyword in voice_name or keyword in voice_id
               for keyword in ['chinese', 'zh', 'cn', '中文', '普通话']):
            print(f"  ✓ 选择中文语音: {voice.name}")
            return voice

    # 如果没找到中文，显示所有语音供选择
    print("  未找到中文语音，以下是可用的语音：")
    for voice in voices[:10]:  # 只显示前10个
        print(f"    - {voice.name}")

    # 返回第一个语音作为默认
    print(f"  使用默认语音: {voices[0].name}")
    return voices[0]


def test_tts():
    """测试 TTS 功能"""
    print("=" * 50)
    print("离线 TTS 测试 Demo")
    print("=" * 50)

    # 初始化引擎
    print("\n[1] 初始化语音引擎...")
    engine = pyttsx3.init()

    # 获取中文语音
    print("\n[2] 查找中文语音...")
    chinese_voice = get_chinese_voice(engine)
    engine.setProperty('voice', chinese_voice.id)

    # 配置参数
    print("\n[3] 配置语音参数...")
    rate = engine.getProperty('rate')
    volume = engine.getProperty('volume')
    print(f"  当前语速: {rate} (正常值约 150-200)")
    print(f"  当前音量: {volume} (正常值 0-1)")

    # 设置参数
    engine.setProperty('rate', 150)  # 稍慢一点，便于听清
    engine.setProperty('volume', 1.0)  # 最大音量

    # 测试文本
    test_texts = [
        "您好，欢迎使用医疗问答助手。",
        "口服，一次3到6克，一日2到3次。",
        "该处方饭前服用效果更佳。",
        "请遵医嘱用药，祝您早日康复。",
    ]

    print("\n[4] 开始语音合成测试...")
    print("-" * 50)

    for i, text in enumerate(test_texts, 1):
        print(f"\n测试 {i}: {text}")
        print("  正在合成...")

        # 合成并播放
        engine.say(text)
        engine.runAndWait()

        print("  ✓ 播放完成")

    print("\n" + "-" * 50)
    print("\n[5] 保存音频文件测试...")

    # 保存为文件
    output_file = "/workspace/projects/test_output.wav"
    print(f"  保存到: {output_file}")

    engine.save_to_file("这是一段测试语音，保存到本地文件中。", output_file)
    engine.runAndWait()

    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"  ✓ 保存成功！文件大小: {file_size} 字节")
    else:
        print("  ✗ 保存失败")

    # 清理
    engine.stop()

    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


def interactive_mode():
    """交互模式：输入文字即时播报"""
    print("\n" + "=" * 50)
    print("交互模式 - 输入文字即时播报")
    print("输入 'quit' 退出")
    print("=" * 50)

    engine = pyttsx3.init()
    chinese_voice = get_chinese_voice(engine)
    engine.setProperty('voice', chinese_voice.id)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)

    while True:
        try:
            text = input("\n请输入要播报的文本: ").strip()

            if text.lower() == 'quit':
                print("退出交互模式")
                break

            if not text:
                print("请输入有效文本")
                continue

            print(f"正在播报: {text}")
            engine.say(text)
            engine.runAndWait()
            print("播放完成")

        except KeyboardInterrupt:
            print("\n\n退出交互模式")
            break

    engine.stop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        test_tts()
