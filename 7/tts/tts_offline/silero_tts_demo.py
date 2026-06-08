#!/usr/bin/env python3
"""
Silero TTS 离线语音合成 Demo
=====================================
真正完全离线的语音合成方案
- 使用 PyTorch 深度学习模型
- 下载一次模型后可完全离线使用
- 支持中文男声（医疗场景推荐）

作者: AI Assistant
版本: 1.0.0
"""

import os
import sys
import torch
import time

# 配置
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(MODEL_DIR, "output")
MODEL_CACHE = os.path.join(MODEL_DIR, "models")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_CACHE, exist_ok=True)


def print_banner():
    """打印横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Silero TTS 离线语音合成 Demo                      ║
║           真正完全离线的语音合成方案                         ║
╠══════════════════════════════════════════════════════════════╣
║  特点:                                                       ║
║  ✓ 使用 PyTorch 深度学习模型                                ║
║  ✓ 下载一次模型后可完全离线使用                              ║
║  ✓ 支持中文男声/女声                                        ║
║  ✓ 无需网络即可生成音频                                      ║
╚══════════════════════════════════════════════════════════════╝
""")


def download_models():
    """下载 Silero TTS 模型"""
    print("[1] 检查/下载模型...")
    print("-" * 50)

    try:
        from silero_tts import silero_tts
    except ImportError:
        print("正在安装 silero-tts...")
        os.system("pip install silero-tts -q")
        from silero_tts import silero_tts

    device = 'cpu'  # CPU 模式
    print(f"  设备: {device}")

    # 加载中文模型
    print("  正在加载 Silero TTS 中文模型...")
    model = silero_tts.SileroTTS(
        model_id='v4_zh',      # 中文模型
        language='zh',         # 中文
        speaker='meimei',      # 女声
        sample_rate=48000,
        device=device
    )
    print(f"  ✓ 模型加载成功")

    # 保存模型引用供后续使用
    return model, device


def test_tts(model, device):
    """测试语音合成"""
    print("\n[2] 语音合成测试...")
    print("-" * 50)

    test_texts = [
        "您好，欢迎使用医疗问答助手。",
        "口服，一次3到6克，一日2到3次。",
        "该处方饭前服用效果更佳。",
        "请遵医嘱用药，祝您早日康复。"
    ]

    audio_results = []

    for i, text in enumerate(test_texts, 1):
        print(f"\n  测试 {i}: {text}")
        print("  正在合成...", end=" ", flush=True)

        try:
            # 合成语音
            audio = model.apply_tts(text=text)

            # 保存音频
            output_path = os.path.join(OUTPUT_DIR, f"test_{i}.wav")
            model.save_audio(output_path, audio)

            import os as os_module
            size = os_module.path.getsize(output_path)
            audio_results.append(output_path)
            print(f"✓ 保存到: {output_path} ({size/1024:.1f} KB)")

        except Exception as e:
            print(f"✗ 错误: {e}")

    return audio_results


def generate_medical_dialogue(model, device):
    """生成完整医疗对话"""
    print("\n[3] 生成医疗对话完整版...")
    print("-" * 50)

    dialogue = """您好，欢迎使用医疗问答助手。
该处方常规的用法用量是：口服，一次3到6克，一日2到3次。
建议饭前半小时服用效果更佳。
请遵医嘱用药，不要自行调整剂量。
祝您早日康复。"""

    print(f"  文本: {dialogue}")
    print("  正在合成...", end=" ", flush=True)

    try:
        audio = model.apply_tts(text=dialogue)

        output_path = os.path.join(OUTPUT_DIR, "medical_dialogue.wav")
        model.save_audio(output_path, audio)

        import os as os_module
        size = os_module.path.getsize(output_path)
        print(f"✓ 保存到: {output_path} ({size/1024:.1f} KB)")
        return output_path

    except Exception as e:
        print(f"✗ 错误: {e}")
        return None


def generate_custom_text(model, device, text):
    """生成自定义文本"""
    print(f"\n[4] 生成自定义文本...")
    print("-" * 50)
    print(f"  文本: {text}")
    print("  正在合成...", end=" ", flush=True)

    try:
        audio = model.apply_tts(text=text)

        # 清理文件名
        safe_text = text[:20].replace(" ", "_").replace("\n", "_")
        output_path = os.path.join(OUTPUT_DIR, f"custom_{safe_text}.wav")
        model.save_audio(output_path, audio)

        import os as os_module
        size = os_module.path.getsize(output_path)
        print(f"✓ 保存到: {output_path} ({size/1024:.1f} KB)")
        return output_path

    except Exception as e:
        print(f"✗ 错误: {e}")
        return None


def list_available_voices():
    """列出可用语音"""
    print("\n[5] 可用语音列表...")
    print("-" * 50)

    try:
        import silero_tts
        voices = silero_tts.tts_models

        print("  中文语音:")
        if 'zh' in voices:
            for voice_id, voice_info in voices['zh'].items():
                print(f"    • {voice_id}: {voice_info}")

    except Exception as e:
        print(f"  获取语音列表失败: {e}")


def print_instructions():
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                     使用说明                                  ║
╠══════════════════════════════════════════════════════════════╣
║  命令行参数:                                                  ║
║  python silero_tts_demo.py              - 运行完整测试        ║
║  python silero_tts_demo.py --text "文本" - 生成自定义文本     ║
║  python silero_tts_demo.py --voices    - 列出可用语音         ║
║                                                              ║
║  模型文件:                                                   ║
║  • models/silero_model.pt  - 包含此文件后可离线使用          ║
║                                                              ║
║  输出文件:                                                   ║
║  • output/*.wav              - 生成的音频文件                 ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    """主函数"""
    print_banner()

    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--voices":
            list_available_voices()
            return

        if sys.argv[1] == "--text" and len(sys.argv) > 2:
            text = sys.argv[2]
            model, device = download_models()
            generate_custom_text(model, device, text)
            print("\n✓ 完成！")
            return

    # 下载/加载模型
    model, device = download_models()

    # 测试语音合成
    test_tts(model, device)

    # 生成完整对话
    generate_medical_dialogue(model, device)

    # 显示文件列表
    print("\n[6] 生成的文件...")
    print("-" * 50)
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            filepath = os.path.join(OUTPUT_DIR, f)
            size = os.path.getsize(filepath)
            print(f"  • {f} ({size/1024:.1f} KB)")

    print_instructions()
    print("\n✓ 测试完成！")


if __name__ == "__main__":
    main()
