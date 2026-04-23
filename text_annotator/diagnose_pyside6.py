#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PySide6 DLL 依赖诊断脚本"""

import os
import sys
import site
import importlib.util
import subprocess
from pathlib import Path


def print_header(title):
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python_env():
    print_header("Python 环境信息")
    print(f"Python 版本: {sys.version}")
    print(f"Python 可执行文件: {sys.executable}")
    print(f"Python 安装目录: {sys.prefix}")
    print(f"conda 环境: {os.environ.get('CONDA_PREFIX', '非 conda 环境')}")
    print(f"平台: {sys.platform}")
    print(f"位数: {'64位' if sys.maxsize > 2**32 else '32位'}")
    print()


def find_pyside6_location():
    print_header("PySide6 安装位置")
    
    try:
        import PySide6
        pyside6_path = Path(PySide6.__file__).parent
        print(f"PySide6 路径: {pyside6_path}")
        
        qt_path = pyside6_path / "Qt"
        if qt_path.exists():
            print(f"Qt 路径: {qt_path}")
            
            qt_plugins = qt_path / "plugins"
            if qt_plugins.exists():
                print(f"Qt 插件路径: {qt_plugins}")
            
            qt_bin = qt_path / "bin"
            if qt_bin.exists():
                print(f"Qt bin 路径: {qt_bin}")
        
        return pyside6_path
    except ImportError as e:
        print(f"PySide6 未安装或无法导入: {e}")
        return None


def list_pyside6_dlls(pyside6_path):
    if not pyside6_path:
        return
    
    print_header("PySide6 DLL 文件检查")
    
    required_dlls = [
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6Network.dll",
        "Qt6OpenGL.dll",
        "Qt6OpenGLWidgets.dll",
        "pyside6.abi3.dll",
        "shiboken6.abi3.dll",
        "Qt6PrintSupport.dll",
        "Qt6Svg.dll",
    ]
    
    pyside6_dlls = list(pyside6_path.glob("*.dll"))
    qt_bin = pyside6_path / "Qt" / "bin"
    qt_dlls = list(qt_bin.glob("*.dll")) if qt_bin.exists() else []
    
    all_dlls = pyside6_dlls + qt_dlls
    dll_names = {dll.name for dll in all_dlls}
    
    print(f"\n找到 {len(all_dlls)} 个 DLL 文件:")
    for dll in sorted(dll_names):
        print(f"  ✓ {dll}")
    
    print(f"\n检查必需的 DLL:")
    missing = []
    for dll in required_dlls:
        if dll in dll_names:
            print(f"  ✓ {dll}")
        else:
            print(f"  ✗ {dll} - 缺失!")
            missing.append(dll)
    
    return missing


def check_qt_plugins(pyside6_path):
    if not pyside6_path:
        return
    
    print_header("Qt 插件检查")
    
    plugins_path = pyside6_path / "Qt" / "plugins"
    
    if not plugins_path.exists():
        print(f"插件路径不存在: {plugins_path}")
        return
    
    required_plugins = [
        "platforms/qwindows.dll",
        "platforms/qoffscreen.dll",
        "styles/qwindowsvistastyle.dll",
        "imageformats/qsvg.dll",
        "imageformats/qico.dll",
        "imageformats/qjpeg.dll",
    ]
    
    print(f"\n插件路径: {plugins_path}")
    
    print("\n检查必需的插件:")
    missing = []
    for plugin in required_plugins:
        plugin_path = plugins_path / plugin
        if plugin_path.exists():
            print(f"  ✓ {plugin}")
        else:
            print(f"  ✗ {plugin} - 缺失!")
            missing.append(plugin)
    
    return missing


def check_msvc_runtime():
    print_header("Visual C++ 运行库检查")
    
    msvc_paths = [
        os.path.expandvars(r"%WINDIR%\System32\msvcp140.dll"),
        os.path.expandvars(r"%WINDIR%\System32\vcruntime140.dll"),
        os.path.expandvars(r"%WINDIR%\System32\vcruntime140_1.dll"),
    ]
    
    found = []
    missing = []
    
    for path in msvc_paths:
        if os.path.exists(path):
            print(f"  ✓ {os.path.basename(path)}")
            found.append(path)
        else:
            print(f"  ✗ {os.path.basename(path)} - 缺失!")
            missing.append(path)
    
    return missing


def try_import_with_workarounds():
    print_header("尝试导入 PySide6（带修复方案）")
    
    original_path = os.environ.get('PATH', '')
    original_dll_directories = []
    
    try:
        import PySide6
        pyside6_path = Path(PySide6.__file__).parent
        
        qt_bin = pyside6_path / "Qt" / "bin"
        qt_plugins = pyside6_path / "Qt" / "plugins"
        qt_platforms = qt_plugins / "platforms"
        
        dll_paths = []
        if qt_bin.exists():
            dll_paths.append(str(qt_bin))
        if pyside6_path.exists():
            dll_paths.append(str(pyside6_path))
        
        print(f"\n尝试添加 DLL 搜索路径...")
        for path in dll_paths:
            if sys.version_info >= (3, 8):
                try:
                    os.add_dll_directory(path)
                    print(f"  ✓ os.add_dll_directory: {path}")
                    original_dll_directories.append(path)
                except Exception as e:
                    print(f"  ✗ os.add_dll_directory 失败: {e}")
            
            if path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
                print(f"  ✓ 添加到 PATH: {path}")
        
        qt_plugin_path = os.environ.get('QT_PLUGIN_PATH', '')
        if qt_plugins.exists() and str(qt_plugins) not in qt_plugin_path:
            os.environ['QT_PLUGIN_PATH'] = str(qt_plugins)
            print(f"  ✓ 设置 QT_PLUGIN_PATH: {qt_plugins}")
        
        print("\n尝试导入 PySide6.QtWidgets...")
        
        importlib.invalidate_caches()
        
        try:
            from PySide6.QtWidgets import QApplication
            print("  ✓ 成功导入 PySide6.QtWidgets!")
            return True
        except ImportError as e:
            print(f"  ✗ 导入失败: {e}")
            return False
        except Exception as e:
            print(f"  ✗ 其他错误: {e}")
            return False
            
    except ImportError as e:
        print(f"  ✗ 无法导入 PySide6: {e}")
        return False
    finally:
        os.environ['PATH'] = original_path


def run_diagnosis():
    print("\n" + "=" * 60)
    print("  PySide6 DLL 依赖诊断工具")
    print("=" * 60 + "\n")
    
    check_python_env()
    
    pyside6_path = find_pyside6_location()
    
    if pyside6_path:
        missing_dlls = list_pyside6_dlls(pyside6_path)
        missing_plugins = check_qt_plugins(pyside6_path)
    else:
        missing_dlls = []
        missing_plugins = []
    
    missing_msvc = check_msvc_runtime()
    
    print_header("诊断总结")
    
    issues = []
    
    if missing_dlls:
        issues.append(f"缺失 {len(missing_dlls)} 个 DLL 文件")
        print(f"✗ 缺失 {len(missing_dlls)} 个 DLL 文件")
    else:
        print("✓ 所有必需的 DLL 都存在")
    
    if missing_plugins:
        issues.append(f"缺失 {len(missing_plugins)} 个 Qt 插件")
        print(f"✗ 缺失 {len(missing_plugins)} 个 Qt 插件")
    else:
        print("✓ 所有必需的 Qt 插件都存在")
    
    if missing_msvc:
        issues.append(f"缺失 {len(missing_msvc)} 个 Visual C++ 运行库")
        print(f"✗ 缺失 {len(missing_msvc)} 个 Visual C++ 运行库")
    else:
        print("✓ Visual C++ 运行库已安装")
    
    print()
    
    if issues:
        print("检测到问题，建议尝试以下解决方案:")
    else:
        print("所有静态检查通过，尝试动态导入测试...")
    
    try_import_with_workarounds()
    
    print()
    print_header("修复建议")
    
    print("""
解决方案 1: 重新安装 PySide6（推荐）
    pip uninstall -y PySide6 PySide6-Addons shiboken6
    pip install PySide6 --no-cache-dir

解决方案 2: 安装 Visual C++ 运行库
    下载并安装:
    https://aka.ms/vs/17/release/vc_redist.x64.exe

解决方案 3: 在代码中添加 DLL 搜索路径
    在导入 PySide6 之前添加:
    
    import os
    from pathlib import Path
    import PySide6
    
    pyside6_path = Path(PySide6.__file__).parent
    qt_bin = pyside6_path / "Qt" / "bin"
    
    if sys.version_info >= (3, 8):
        os.add_dll_directory(str(qt_bin))
        os.add_dll_directory(str(pyside6_path))
    
    os.environ['PATH'] = str(qt_bin) + os.pathsep + os.environ.get('PATH', '')
    os.environ['QT_PLUGIN_PATH'] = str(pyside6_path / "Qt" / "plugins")

解决方案 4: 使用 conda 安装（如果在 conda 环境）
    conda install -c conda-forge pyside6

解决方案 5: 检查并安装 qt6 依赖
    pip install PySide6-Addons
""")
    
    return len(issues)


if __name__ == "__main__":
    exit_code = run_diagnosis()
    sys.exit(exit_code)
