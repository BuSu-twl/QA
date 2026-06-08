"""
医疗问答助手 - Windows EXE 打包构建脚本

使用方法:
    1. 安装依赖:  pip install pyinstaller flask openpyxl pyttsx3 edge-tts aiohttp
    2. 执行打包:  python build_exe.py
    3. 输出目录:  dist/

打包完成后，将 dist/ 目录中的所有文件复制到目标 Windows 电脑即可使用。
"""
import os
import sys
import shutil
import subprocess

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 打包输出目录
DIST_DIR = os.path.join(BASE_DIR, 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build')


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', '--version'],
            capture_output=True, text=True
        )
        version = result.stdout.strip()
        print(f"[OK] PyInstaller 已安装: {version}")
        return True
    except Exception:
        print("[X] PyInstaller 未安装")
        print("    请运行: pip install pyinstaller")
        return False


def check_dependencies(auto_install=True):
    """检查项目依赖，可选自动安装"""
    deps = {
        'flask': 'flask',
        'openpyxl': 'openpyxl',
        'edge_tts': 'edge-tts',
        'pyttsx3': 'pyttsx3',
        # Edge-TTS 运行时依赖
        'aiohttp': 'aiohttp',
        'certifi': 'certifi',
        'tabulate': 'tabulate',
    }

    missing = []
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[X] {package} 未安装")
            missing.append(package)

    if missing and auto_install:
        print(f"\n正在自动安装缺失依赖: {', '.join(missing)}")
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install'] + missing,
                check=True
            )
            print("[OK] 依赖安装完成")
            missing = []  # 安装后重置
        except subprocess.CalledProcessError:
            print("[X] 自动安装失败，请手动运行:")
            print(f"    pip install {' '.join(missing)}")

    # Edge-TTS 是必须依赖，没有它无法使用男声
    if 'edge-tts' in missing:
        print("\n[!] Edge-TTS 是必须依赖！")
        print("    没有 Edge-TTS，语音合成只能使用 Windows 默认女声（Huihui）。")
        print("    请确保安装: pip install edge-tts")
        print()
        resp = input("是否继续打包（语音将为女声）？[y/N]: ").strip().lower()
        if resp != 'y':
            print("[X] 打包已取消")
            sys.exit(1)

    return missing


def check_data_files():
    """检查必要的数据文件"""
    required_files = [
        'data/question.xlsx',
        'data/answer.xlsx',
        'templates/index.html',
        'templates/login.html',
    ]

    all_exist = True
    for f in required_files:
        path = os.path.join(BASE_DIR, f)
        if os.path.exists(path):
            print(f"[OK] {f}")
        else:
            print(f"[X] {f} 不存在")
            all_exist = False

    return all_exist


def clean_build():
    """清理之前的构建"""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"[OK] 已清理: {d}")


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    spec_file = os.path.join(BASE_DIR, 'qa_assistant.spec')

    if not os.path.exists(spec_file):
        print("[X] spec 文件不存在: " + spec_file)
        return False

    print("\n" + "=" * 50)
    print("开始打包...")
    print("=" * 50 + "\n")

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--workpath', os.path.join(BASE_DIR, 'build'),
        '--distpath', os.path.join(BASE_DIR, 'dist'),
        spec_file
    ]
    print(f"执行: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        print("\n[OK] PyInstaller 打包成功")
        return True
    else:
        print("\n[X] PyInstaller 打包失败")
        return False


def post_build():
    """打包后处理：复制外部数据文件到 dist 目录"""
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)

    # 1. 复制 data 目录（用户需要修改的文件，放在 exe 外部）
    data_dest = os.path.join(DIST_DIR, 'data')
    if os.path.exists(data_dest):
        shutil.rmtree(data_dest)
    shutil.copytree(os.path.join(BASE_DIR, 'data'), data_dest)
    print(f"[OK] 复制 data/ 到 dist/data/")

    # 2. 复制 templates 目录（放在 exe 外部，方便修改页面）
    tmpl_dest = os.path.join(DIST_DIR, 'templates')
    if os.path.exists(tmpl_dest):
        shutil.rmtree(tmpl_dest)
    shutil.copytree(os.path.join(BASE_DIR, 'templates'), tmpl_dest)
    print(f"[OK] 复制 templates/ 到 dist/templates/")

    # 3. 复制 static 目录（头像、图标等静态资源）
    static_src = os.path.join(BASE_DIR, 'static')
    if os.path.exists(static_src):
        static_dest = os.path.join(DIST_DIR, 'static')
        if os.path.exists(static_dest):
            shutil.rmtree(static_dest)
        shutil.copytree(static_src, static_dest)
        print(f"[OK] 复制 static/ 到 dist/static/")

    # 4. 复制 models 目录（如果存在）
    models_src = os.path.join(BASE_DIR, 'models')
    if os.path.exists(models_src) and any(
        os.path.isfile(os.path.join(models_src, f)) for f in os.listdir(models_src)
    ):
        models_dest = os.path.join(DIST_DIR, 'models')
        if os.path.exists(models_dest):
            shutil.rmtree(models_dest)
        shutil.copytree(models_src, models_dest)
        print(f"[OK] 复制 models/ 到 dist/models/")

    # 5. 复制 audio 目录（预生成的语音文件，实现离线高质量语音）
    audio_src = os.path.join(BASE_DIR, 'audio')
    if os.path.exists(audio_src) and any(
        os.path.isfile(os.path.join(audio_src, f)) for f in os.listdir(audio_src)
    ):
        audio_dest = os.path.join(DIST_DIR, 'audio')
        if os.path.exists(audio_dest):
            shutil.rmtree(audio_dest)
        shutil.copytree(audio_src, audio_dest)
        # 计算音频总大小
        total_audio_size = sum(
            os.path.getsize(os.path.join(audio_dest, f))
            for f in os.listdir(audio_dest)
            if os.path.isfile(os.path.join(audio_dest, f))
        )
        print(f"[OK] 复制 audio/ 到 dist/audio/ ({total_audio_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"[!] audio/ 目录不存在或为空（可选：运行 python generate_audio.py 生成预语音）")

    # 6. 创建启动脚本
    bat_content = r'''@echo off
chcp 65001 >nul
title QAAssistant
echo ================================================
echo        Medical QA Assistant
echo ================================================
echo.

:: 切换到 bat 所在目录，避免路径问题
cd /d "%~dp0"

:: 直接在当前窗口运行 exe（可以看到错误信息）
"QAAssistant.exe"

:: 如果 exe 退出，暂停显示错误
echo.
echo Service has stopped.
pause
'''
    bat_path = os.path.join(DIST_DIR, 'start.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    print(f"[OK] 创建 start.bat")

    # 6. 创建使用说明
    readme = '''================================================
        QA Assistant - Offline Version
================================================

[Quick Start]

  Option 1: Double click "start.bat"
    -> Auto start program and open browser

  Option 2: Double click "QAAssistant.exe"
    -> Manually visit http://localhost:5000 in browser

[Login Password]
  xxx

[Files]

  QAAssistant.exe    Main program
  start.bat          Quick start script
  data/              Knowledge base (editable)
    question.xlsx    Questions
    answer.xlsx      Answers
  templates/         Page templates (editable)
  audio/             Pre-generated voice files (offline TTS)
  models/            Voice models (optional)

[Edit Knowledge Base]
  1. Open data/question.xlsx to edit questions
  2. Open data/answer.xlsx to edit answers
  3. Click "Refresh KB" button on page, or restart program

[Pre-generate Audio (Recommended)]
  Run before packaging for offline high-quality voice:
    python generate_audio.py

[Voice Priority]
  1. Pre-generated audio files (offline, best quality)
  2. Windows built-in voice Pyttsx3/SAPI5 (offline, decent quality)
  3. Edge-TTS online (requires internet, best quality)

[Notes]
  - Make sure port 5000 is available
  - Press Ctrl+C in console to stop
  - Restart after editing knowledge base

================================================
'''
    readme_path = os.path.join(DIST_DIR, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme)
    print(f"[OK] 创建 README.txt")

    # 7. 创建 requirements.txt（方便用户了解依赖）
    req_content = '''# 医疗问答助手 - 依赖列表（仅供参考，exe 已包含）
flask>=2.0.0
openpyxl>=3.0.0
edge-tts>=6.1.0
pyttsx3>=2.90
'''
    req_path = os.path.join(DIST_DIR, 'requirements.txt')
    with open(req_path, 'w', encoding='utf-8') as f:
        f.write(req_content)
    print(f"[OK] 创建 requirements.txt")


def print_summary():
    """打印打包结果摘要"""
    print("\n" + "=" * 50)
    print("打包完成！")
    print("=" * 50)
    print(f"\n输出目录: {DIST_DIR}")
    print("\n目录结构:")
    for root, dirs, files in os.walk(DIST_DIR):
        level = root.replace(DIST_DIR, '').count(os.sep)
        indent = '  ' * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = '  ' * (level + 1)
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            if size > 1024 * 1024:
                size_str = f'{size / 1024 / 1024:.1f}MB'
            elif size > 1024:
                size_str = f'{size / 1024:.1f}KB'
            else:
                size_str = f'{size}B'
            print(f'{subindent}{file} ({size_str})')

    print("\n使用方法:")
    print("  1. 将 dist/ 目录中所有文件复制到目标 Windows 电脑")
    print("  2. 双击 启动助手.bat 或 医疗问答助手.exe")
    print("  3. 浏览器访问 http://localhost:5000")
    print("  4. 输入口令: 香连止痢丸")
    print("=" * 50)


def main():
    print("=" * 50)
    print("医疗问答助手 - Windows EXE 打包工具")
    print("=" * 50)
    print()

    # 步骤 1: 检查 PyInstaller
    print("[1/6] 检查 PyInstaller...")
    if not check_pyinstaller():
        sys.exit(1)
    print()

    # 步骤 2: 检查依赖
    print("[2/6] 检查项目依赖...")
    missing = check_dependencies()
    if missing:
        print(f"\n缺少必要依赖: {', '.join(missing)}")
        print(f"请运行: pip install {' '.join(missing)}")
        sys.exit(1)
    print()

    # 步骤 3: 检查数据文件
    print("[3/7] 检查数据文件...")
    if not check_data_files():
        print("\n缺少必要的数据文件，请检查项目完整性")
        sys.exit(1)
    print()

    # 步骤 4: 检查/生成预生成音频
    print("[4/7] 检查预生成音频...")
    audio_dir = os.path.join(BASE_DIR, 'audio')
    need_generate = True
    if os.path.exists(audio_dir):
        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
        if audio_files:
            total_size = sum(os.path.getsize(os.path.join(audio_dir, f)) for f in audio_files)
            print(f"[OK] 已有 {len(audio_files)} 个预生成音频文件 ({total_size / 1024 / 1024:.1f} MB)")
            need_generate = False
        else:
            print("[!] audio/ 目录为空")
    else:
        print("[!] 未找到 audio/ 目录")

    if need_generate:
        # 尝试用 Edge-TTS 预生成音频（需要网络）
        try:
            import edge_tts  # noqa
            print("[*] 正在用 Edge-TTS 预生成音频文件...")
            gen_script = os.path.join(BASE_DIR, 'generate_audio.py')
            result = subprocess.run(
                [sys.executable, gen_script],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                print("[OK] 音频文件预生成完成")
            else:
                print(f"[!] 音频预生成失败: {result.stderr[:200]}")
                print("    语音将使用 Windows SAPI5（可能是女声）")
        except ImportError:
            print("[!] Edge-TTS 未安装，无法预生成音频")
            print("    打包后语音将使用 Windows SAPI5（可能是女声）")
            print("    建议: pip install edge-tts 后重新打包")
        except Exception as e:
            print(f"[!] 音频预生成出错: {e}")
            print("    语音将使用 Windows SAPI5（可能是女声）")
    print()

    # 步骤 5: 清理旧构建
    print("[5/7] 清理旧构建...")
    clean_build()
    print()

    # 步骤 6: 执行打包
    print("[6/7] 执行 PyInstaller 打包...")
    if not run_pyinstaller():
        print("\n打包失败，请检查错误信息")
        sys.exit(1)
    print()

    # 步骤 7: 打包后处理
    print("[7/7] 处理打包输出...")
    post_build()
    print()

    # 打印结果
    print_summary()


if __name__ == '__main__':
    main()
