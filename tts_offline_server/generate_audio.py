#!/usr/bin/env python3
"""
预生成音频文件脚本
==================
在有网络的环境下运行此脚本，使用 Edge-TTS 为知识库中的所有答案生成音频文件。
生成的音频文件保存到 audio/ 目录，打包时一起打包进 exe，实现离线语音播报。

使用方法：
  python generate_audio.py              # 生成所有答案的音频
  python generate_audio.py --voice zh-CN-XiaoxiaoNeural  # 指定语音
  python generate_audio.py --force      # 强制重新生成（覆盖已有音频）
"""

import os
import sys
import asyncio
import hashlib

# 当前目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

AUDIO_DIR = os.path.join(SCRIPT_DIR, 'audio')


def get_text_hash(text: str) -> str:
    """获取文本的哈希值作为文件名"""
    clean_text = ''.join(c for c in text if c not in ' \n\t.,。，')
    return hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:12]


async def synthesize(text: str, voice: str, output_file: str) -> bool:
    """使用 Edge-TTS 合成语音到文件"""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        with open(output_file, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
        return True
    except Exception as e:
        print(f"  合成失败: {e}")
        return False


async def main():
    voice = "zh-CN-YunyangNeural"  # 默认云扬（沉稳男声）
    force = False

    # 解析参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--voice' and i + 1 < len(args):
            voice = args[i + 1]
            i += 2
        elif args[i] == '--force':
            force = True
            i += 1
        else:
            i += 1

    print("=" * 60)
    print("  预生成音频文件工具")
    print("=" * 60)
    print(f"  语音: {voice}")
    print(f"  强制重新生成: {'是' if force else '否'}")
    print(f"  输出目录: {AUDIO_DIR}")
    print()

    # 确保输出目录存在
    os.makedirs(AUDIO_DIR, exist_ok=True)

    # 检查 edge-tts 是否可用
    try:
        import edge_tts
    except ImportError:
        print("[错误] edge-tts 未安装，请先安装: pip install edge-tts")
        sys.exit(1)

    # 加载知识库
    from knowledge_base import init_knowledge_base, QA_DIRECT, QUESTIONS, QA_PAIRS
    import knowledge_base as kb
    init_knowledge_base()

    # 收集所有需要生成音频的文本（答案）
    # 注意：直接使用 kb 模块的变量，因为 init_knowledge_base 修改的是模块级 global
    texts_to_generate = set()

    # 从 QA_DIRECT 获取所有问答对
    for qa in kb.QA_DIRECT:
        answer = qa.get('answer', '').strip()
        if answer:
            texts_to_generate.add(answer)

    # 从 QA_PAIRS 获取答案
    for qa in kb.QA_PAIRS:
        answer = qa.get('answer', '').strip()
        if answer:
            texts_to_generate.add(answer)

    print(f"  知识库中共有 {len(texts_to_generate)} 条不同的答案需要生成音频")
    print()

    # 生成音频
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, text in enumerate(texts_to_generate, 1):
        text_hash = get_text_hash(text)
        output_file = os.path.join(AUDIO_DIR, f"{text_hash}.mp3")

        # 检查是否已存在
        if os.path.exists(output_file) and not force:
            size = os.path.getsize(output_file)
            if size > 100:  # 有效音频文件
                skip_count += 1
                print(f"  [{i}/{len(texts_to_generate)}] 跳过（已存在）: {text[:40]}...")
                continue

        print(f"  [{i}/{len(texts_to_generate)}] 生成中: {text[:40]}...", end=" ", flush=True)

        ok = await synthesize(text, voice, output_file)
        if ok:
            size = os.path.getsize(output_file)
            print(f"OK ({size / 1024:.1f} KB)")
            success_count += 1
        else:
            fail_count += 1
            # 删除失败的文件
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception:
                    pass

    print()
    print("=" * 60)
    print(f"  生成完成！")
    print(f"  新生成: {success_count} 个")
    print(f"  已跳过: {skip_count} 个")
    print(f"  失败: {fail_count} 个")
    print(f"  音频目录: {AUDIO_DIR}")

    # 统计目录大小
    total_size = 0
    file_count = 0
    for f in os.listdir(AUDIO_DIR):
        fp = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(fp):
            total_size += os.path.getsize(fp)
            file_count += 1

    print(f"  总计: {file_count} 个文件, {total_size / 1024 / 1024:.1f} MB")
    print("=" * 60)

    if fail_count > 0:
        print("\n[提示] 部分音频生成失败，可能是网络问题。请检查网络后重试。")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
