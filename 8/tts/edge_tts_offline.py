#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge-TTS 离线模式 TTS 模块
用于医疗问答助手的语音合成

使用方法:
    from edge_tts_offline import EdgeTTSOffline

    tts = EdgeTTSOffline()
    # 生成音频文件
    tts.synthesize("口服，一次3到6克", "output.mp3")
    # 或获取音频数据
    audio_data = tts.synthesize_to_bytes("口服，一次3到6克")
"""

import asyncio
import os
import sys
from pathlib import Path

# 尝试导入 edge_tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("警告: edge-tts 未安装，请运行: pip install edge-tts")


class EdgeTTSOffline:
    """Edge-TTS 离线模式语音合成类"""

    # 默认使用云扬（沉稳男声）- 医疗场景推荐
    DEFAULT_VOICE = "zh-CN-YunyangNeural"

    # 可用中文语音列表
    VOICES = {
        # 女声
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",      # 晓晓（默认女声）
        "xiaoyi": "zh-CN-XiaoyiNeural",          # 小艺

        # 男声
        "yunjian": "zh-CN-YunjianNeural",        # 云健
        "yunxi": "zh-CN-YunxiNeural",            # 云希（年轻男声）
        "yunxia": "zh-CN-YunxiaNeural",          # 云夏
        "yunyang": "zh-CN-YunyangNeural",       # 云扬（沉稳男声）⭐ 医疗推荐

        # 方言
        "xiaobei": "zh-CN-liaoning-XiaobeiNeural",  # 东北话女声
        "xiaoni": "zh-CN-shaanxi-XiaoniNeural",     # 陕西话女声
    }

    def __init__(self, voice: str = None, cache_dir: str = None):
        """
        初始化 Edge-TTS 离线模式

        Args:
            voice: 语音名称，可选值: xiaoxiao, xiaoyi, yunjian, yunxi, yunxia, yunyang, xiaobei, xiaoni
                  默认使用 yunyang（沉稳男声，医疗场景推荐）
            cache_dir: 模型缓存目录，默认使用 ~/.cache/edge-tts
        """
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts 未安装，请运行: pip install edge-tts")

        if voice:
            self.voice = self.VOICES.get(voice.lower(), self.DEFAULT_VOICE)
        else:
            self.voice = self.DEFAULT_VOICE

        # 设置缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # 默认缓存目录: ~/.cache/edge-tts
            cache_home = os.environ.get('CACHE_HOME', os.path.expanduser('~/.cache'))
            self.cache_dir = Path(cache_home) / 'edge-tts'

        self.Communicate = edge_tts.Communicate
        self.list_voices = edge_tts.list_voices

    def get_cache_status(self) -> dict:
        """
        获取模型缓存状态

        Returns:
            dict: 包含缓存状态的字典
        """
        cache_info = {
            "cache_dir": str(self.cache_dir),
            "exists": self.cache_dir.exists(),
            "files": []
        }

        if self.cache_dir.exists():
            cache_info["files"] = [
                f.name for f in self.cache_dir.rglob("*")
                if f.is_file()
            ]

        return cache_info

    def synthesize(self, text: str, output_file: str = None,
                   voice: str = None, rate: str = "+0%", volume: str = "+0%") -> str:
        """
        合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_file: 输出文件路径（MP3格式）
            voice: 语音名称（可选，会覆盖初始化时的设置）
            rate: 语速，如 "+10%", "-10%", "+0%"
            volume: 音量，如 "+10%", "-10%", "+0%"

        Returns:
            str: 输出文件路径

        Raises:
            Exception: 合成失败时抛出异常
        """
        voice_to_use = self.VOICES.get(voice.lower(), self.voice) if voice else self.voice

        if not output_file:
            # 生成默认文件名
            text_preview = text[:10].replace(" ", "_").replace("\n", "_")
            output_file = f"tts_output_{text_preview}.mp3"

        async def _synthesize():
            try:
                communicate = self.Communicate(
                    text=text,
                    voice=voice_to_use,
                    rate=rate,
                    volume=volume
                )
                await communicate.save(output_file)
                return output_file
            except Exception as e:
                raise Exception(f"语音合成失败: {str(e)}")

        try:
            result = asyncio.run(_synthesize())
            return result
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}")

    def synthesize_to_bytes(self, text: str, voice: str = None,
                           rate: str = "+0%", volume: str = "+0%") -> bytes:
        """
        合成语音并返回字节数据

        Args:
            text: 要合成的文本
            voice: 语音名称（可选）
            rate: 语速
            volume: 音量

        Returns:
            bytes: MP3 格式的音频数据

        Raises:
            Exception: 合成失败时抛出异常
        """
        voice_to_use = self.VOICES.get(voice.lower(), self.voice) if voice else self.voice

        async def _synthesize():
            try:
                communicate = self.Communicate(
                    text=text,
                    voice=voice_to_use,
                    rate=rate,
                    volume=volume
                )
                return await communicate.get_audio_data()
            except Exception as e:
                raise Exception(f"语音合成失败: {str(e)}")

        try:
            return asyncio.run(_synthesize())
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}")

    @staticmethod
    def get_available_voices() -> dict:
        """
        获取所有可用的语音

        Returns:
            dict: 语音名称到语音ID的映射
        """
        return EdgeTTSOffline.VOICES.copy()


async def list_available_voices():
    """异步获取可用的语音列表（需要联网）"""
    try:
        voices = await edge_tts.list_voices()
        zh_voices = [v for v in voices if v['Locale'].startswith('zh')]
        return zh_voices
    except Exception as e:
        return []


def main():
    """命令行测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Edge-TTS 离线模式语音合成")
    parser.add_argument("-t", "--text", type=str, help="要合成的文本")
    parser.add_argument("-o", "--output", type=str, help="输出文件路径")
    parser.add_argument("-v", "--voice", type=str, default="yunyang",
                       help="语音名称: xiaoxiao, xiaoyi, yunjian, yunxi, yunxia, yunyang, xiaobei, xiaoni")
    parser.add_argument("--list", action="store_true", help="列出所有可用的语音")
    parser.add_argument("--cache", action="store_true", help="显示缓存状态")

    args = parser.parse_args()

    if args.list:
        print("\n可用语音列表:")
        print("-" * 60)
        for name, voice_id in EdgeTTSOffline.VOICES.items():
            marker = " ⭐ 医疗推荐" if name == "yunyang" else ""
            print(f"  {name:12} -> {voice_id}{marker}")
        print("-" * 60)
        print("\n获取详细列表（需要联网）...")
        voices = asyncio.run(list_available_voices())
        if voices:
            print("\n所有中文语音:")
            for v in voices[:20]:
                print(f"  {v['Name']} | {v['Locale']} | {v['Gender']}")
        return

    if args.cache:
        tts = EdgeTTSOffline()
        status = tts.get_cache_status()
        print(f"\n缓存目录: {status['cache_dir']}")
        print(f"目录存在: {status['exists']}")
        print(f"文件数量: {len(status['files'])}")
        if status['files']:
            print("\n文件列表:")
            for f in status['files'][:20]:
                print(f"  {f}")
        return

    if args.text:
        tts = EdgeTTSOffline(voice=args.voice)
        output = args.output or f"output_{args.voice}.mp3"
        print(f"正在合成: {args.text[:50]}...")
        print(f"使用语音: {tts.voice}")
        try:
            result = tts.synthesize(args.text, output)
            print(f"✓ 合成成功: {result}")
        except Exception as e:
            print(f"✗ 合成失败: {e}")
    else:
        # 默认测试
        test_texts = [
            "您好，欢迎使用医疗问答助手。",
            "口服，一次3到6克，一日2到3次。",
            "该处方饭前服用效果更佳。",
            "请遵医嘱用药，祝您早日康复。"
        ]

        tts = EdgeTTSOffline(voice=args.voice)
        print(f"\n使用语音: {tts.voice}")
        print("-" * 50)

        for i, text in enumerate(test_texts, 1):
            print(f"\n测试 {i}: {text}")
            try:
                result = tts.synthesize(text, f"test_{i}_{args.voice}.mp3")
                print(f"✓ 已保存: {result}")
            except Exception as e:
                print(f"✗ 失败: {e}")

        print("\n" + "-" * 50)
        print("测试完成!")


if __name__ == "__main__":
    main()
