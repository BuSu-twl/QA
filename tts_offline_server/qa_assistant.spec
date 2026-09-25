# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 医疗问答助手离线版

使用方法:
    pip install pyinstaller
    pyinstaller --clean qa_assistant.spec

或使用构建脚本:
    python build_exe.py
"""
import os
import sys
import glob

block_cipher = None

# 项目根目录（仅限 tts_offline_server，不要向上查找）
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

# 确保不会扫描到上级目录的旧版模块
_PATH_EX = [BASE_DIR]

# 需要打包进 exe 内部的数据文件
datas = [
    (os.path.join(BASE_DIR, 'templates'), 'templates'),
    (os.path.join(BASE_DIR, 'data'), 'data'),
]

# 如果 models 目录存在且有文件，也打包进去
models_dir = os.path.join(BASE_DIR, 'models')
if os.path.exists(models_dir) and any(
    os.path.isfile(os.path.join(models_dir, f)) for f in os.listdir(models_dir)
):
    datas.append((models_dir, 'models'))

# 如果 audio 目录存在（预生成的语音文件），也打包进去
audio_dir = os.path.join(BASE_DIR, 'audio')
if os.path.exists(audio_dir) and any(
    os.path.isfile(os.path.join(audio_dir, f)) for f in os.listdir(audio_dir)
):
    datas.append((audio_dir, 'audio'))

# 如果 static 目录存在，也打包进去
static_dir = os.path.join(BASE_DIR, 'static')
if os.path.exists(static_dir):
    datas.append((static_dir, 'static'))

# 如果有 .ico 图标文件，设置图标路径
icon_path = None
icon_file = os.path.join(BASE_DIR, 'static', 'icon.ico')
if os.path.exists(icon_file):
    try:
        with open(icon_file, 'rb') as f:
            header = f.read(4)
        if header[:2] == b'\x00\x00' or header[:4] == b'\x00\x00\x01\x00':
            icon_path = icon_file
        else:
            print("[WARN] icon.ico 不是有效的 ICO 格式，跳过图标")
            try:
                from PIL import Image
                png_file = os.path.join(BASE_DIR, 'static', 'icon.ico')
                if os.path.exists(png_file):
                    img = Image.open(png_file)
                    img.save(icon_file, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
                    icon_path = icon_file
                    print("[OK] 已从 PNG 自动转换为 ICO 格式")
            except ImportError:
                print("[提示] 安装 Pillow 可自动转换: pip install Pillow")
            except Exception as e:
                print(f"[WARN] PNG 转 ICO 失败: {e}")
    except Exception as e:
        print(f"[WARN] 读取图标文件失败: {e}")


def _collect_all_binaries():
    """
    彻底收集所有必要的 DLL/pyd 文件。
    重点解决 Anaconda 环境下 pyexpat/libexpat DLL 加载失败问题。
    """
    binaries = []
    found_files = set()

    def _add_file(filepath, dest='.'):
        """添加文件到 binaries，避免重复"""
        abspath = os.path.abspath(filepath)
        if abspath not in found_files and os.path.exists(abspath):
            found_files.add(abspath)
            binaries.append((abspath, dest))

    # 1. 收集 pyexpat 和 _elementtree 的 .pyd 文件
    for mod_name in ['pyexpat', '_elementtree', '_hashlib', '_ssl', 'select',
                     '_bz2', '_lzma', '_socket', '_ctypes', '_queue',
                     '_multiprocessing', 'unicodedata', '_decimal']:
        try:
            mod = __import__(mod_name)
            if hasattr(mod, '__file__') and mod.__file__:
                _add_file(mod.__file__)

                # 查找该 .pyd 依赖的 DLL（Anaconda 中 .pyd 依赖 DLLs/ 或 Library/bin/ 下的 DLL）
                mod_dir = os.path.dirname(mod.__file__)

                # 2. 向上查找 Anaconda 环境的根目录
                # Anaconda 结构: envs/myenv/Lib/site-packages/xxx.pyd
                #                envs/myenv/DLLs/
                #                envs/myenv/Library/bin/
                env_root = mod_dir
                for _ in range(5):
                    parent = os.path.dirname(env_root)
                    if os.path.exists(os.path.join(parent, 'DLLs')) or \
                       os.path.exists(os.path.join(parent, 'Library')):
                        env_root = parent
                        break
                    env_root = parent

                # 3. 从 DLLs 和 Library/bin 收集关键 DLL
                for dll_dir in [
                    os.path.join(env_root, 'DLLs'),
                    os.path.join(env_root, 'Library', 'bin'),
                    os.path.join(env_root),  # 有时 DLL 直接在根目录
                ]:
                    if not os.path.isdir(dll_dir):
                        continue
                    for dll_name in [
                        'libexpat.dll', 'expat.dll', 'libexpatd.dll',
                        'libcrypto-3-x64.dll', 'libcrypto-3.dll',
                        'libssl-3-x64.dll', 'libssl-3.dll',
                        'libffi-8.dll', 'libffi-7.dll', 'libffi-6.dll',
                        'zlib.dll', 'zlib1.dll',
                        'liblzma.dll', 'libbz2.dll',
                        'python311.dll', 'python310.dll', 'python312.dll',
                    ]:
                        dll_path = os.path.join(dll_dir, dll_name)
                        if os.path.exists(dll_path):
                            _add_file(dll_path)

                    # 通配符匹配版本化的 DLL
                    for pattern in ['libcrypto-*.dll', 'libssl-*.dll', 'libffi-*.dll',
                                    'python3*.dll', 'libexpat*.dll']:
                        for dll_path in glob.glob(os.path.join(dll_dir, pattern)):
                            _add_file(dll_path)

        except ImportError:
            pass

    # 4. 查找 python3xx.dll（必须在 PATH 或 sys.prefix 中）
    python_dll = f'python{sys.version_info.major}{sys.version_info.minor}.dll'
    for search_dir in [sys.prefix, os.path.join(sys.prefix, 'DLLs')]:
        dll_path = os.path.join(search_dir, python_dll)
        if os.path.exists(dll_path):
            _add_file(dll_path)

    # 5. 使用 PyInstaller 的 collect_dynamic_libs 收集已知包的 DLL
    try:
        from PyInstaller.utils.hooks import collect_dynamic_libs
        for pkg in ['openpyxl', 'cryptography']:
            try:
                pkg_binaries = collect_dynamic_libs(pkg)
                for b in pkg_binaries:
                    _add_file(b[0], b[1])
            except Exception:
                pass
    except ImportError:
        pass

    if binaries:
        print(f"[INFO] 收集到 {len(binaries)} 个二进制文件:")
        for b in binaries:
            print(f"  {os.path.basename(b[0])}")
    else:
        print("[WARN] 未收集到额外的二进制文件")

    return binaries


# 隐式导入（PyInstaller 无法自动检测的模块）
hiddenimports = [
    # Flask 生态
    'flask', 'jinja2', 'werkzeug', 'click', 'itsdangerous', 'MarkupSafe',
    'blinker',

    # openpyxl 依赖
    'openpyxl', 'openpyxl.cell', 'openpyxl.cell._writer',
    'openpyxl.workbook', 'openpyxl.worksheet',
    'openpyxl.styles', 'openpyxl.styles.builtins',
    'openpyxl.chart', 'openpyxl.xml.functions',
    'openpyxl.xml.constants',
    'et_xmlfile',

    # XML 解析（解决 pyexpat 问题）
    'xml', 'xml.etree', 'xml.etree.ElementTree',
    'xml.parsers', 'xml.parsers.expat',
    'pyexpat', '_elementtree',

    # edge-tts 全部子模块
    'edge_tts', 'edge_tts.communicate', 'edge_tts.constants',
    'edge_tts.data_classes', 'edge_tts.drm', 'edge_tts.exceptions',
    'edge_tts.submaker', 'edge_tts.typing', 'edge_tts.util',
    'edge_tts.version', 'edge_tts.voices',

    # edge-tts 运行时依赖
    'aiohttp', 'aiohttp.client', 'aiohttp.connector',
    'aiohttp.client_reqrep', 'aiohttp.client_ws',
    'aiohttp.formdata', 'aiohttp.hdrs', 'aiohttp.helpers',
    'aiohttp.http', 'aiohttp.http_parser', 'aiohttp.http_writer',
    'aiohttp.multipart', 'aiohttp.payload',
    'aiohttp.streams', 'aiohttp.tracing', 'aiohttp.web',
    'aiosignal', 'frozenlist', 'multidict', 'yarl', 'propcache',
    'certifi', 'tabulate', 'ssl',

    # pyttsx3
    'pyttsx3', 'pyttsx3.drivers', 'pyttsx3.drivers.sapi5',
    'comtypes', 'comtypes.client', 'comtypes.gen',
    'pythoncom', 'pywintypes',

    # 异步
    'asyncio', 'concurrent', 'concurrent.futures',

    # 标准库补充
    'logging', 'logging.handlers', 'hashlib', 'tempfile',
    'urllib', 'urllib.parse',
]

# 排除大型不必要的包（减小 exe 体积）
excludes = [
    'numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn',
    'tkinter', 'unittest', 'pydoc', 'doctest',
    'distutils', 'setuptools', 'pip',
    'tornado', 'sqlalchemy',
]

a = Analysis(
    ['app.py'],
    pathex=_PATH_EX,
    binaries=_collect_all_binaries(),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QAAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QAAssistant',
)
