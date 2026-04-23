import sys
import os
import site
import importlib.util
from pathlib import Path


def find_pyside6_path():
    """在不导入 PySide6 的情况下查找其安装路径"""
    
    try:
        spec = importlib.util.find_spec("PySide6")
        if spec and spec.origin:
            return Path(spec.origin).parent
    except Exception:
        pass
    
    try:
        for site_packages in site.getsitepackages():
            pyside6_path = Path(site_packages) / "PySide6"
            if pyside6_path.exists():
                return pyside6_path
    except Exception:
        pass
    
    try:
        user_site = Path(site.getusersitepackages()) / "PySide6"
        if user_site.exists():
            return user_site
    except Exception:
        pass
    
    for path in sys.path:
        if not path:
            continue
        pyside6_path = Path(path) / "PySide6"
        if pyside6_path.exists():
            return pyside6_path
    
    return None


def setup_pyside6_env():
    """在导入 PySide6.QtWidgets 之前设置 DLL 搜索路径"""
    
    pyside6_path = find_pyside6_path()
    if not pyside6_path:
        return False
    
    paths_to_add = []
    
    paths_to_add.append(str(pyside6_path))
    
    qt_plugins = pyside6_path / "plugins"
    if qt_plugins.exists():
        paths_to_add.append(str(qt_plugins))
        
        platforms_dir = qt_plugins / "platforms"
        if platforms_dir.exists():
            paths_to_add.append(str(platforms_dir))
    
    qt_qml = pyside6_path / "qml"
    if qt_qml.exists():
        paths_to_add.append(str(qt_qml))
    
    qt_lib = pyside6_path / "lib"
    if qt_lib.exists():
        paths_to_add.append(str(qt_lib))
    
    conda_bin = Path(sys.prefix) / "Library" / "bin"
    if conda_bin.exists():
        paths_to_add.append(str(conda_bin))
    
    conda_lib_bin = Path(sys.prefix) / "Library" / "lib"
    if conda_lib_bin.exists():
        paths_to_add.append(str(conda_lib_bin))
    
    for path in paths_to_add:
        if sys.version_info >= (3, 8):
            try:
                os.add_dll_directory(path)
            except Exception:
                pass
        
        if path not in os.environ.get('PATH', ''):
            os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
    
    if qt_plugins.exists():
        current_qt_plugin_path = os.environ.get('QT_PLUGIN_PATH', '')
        qt_plugins_str = str(qt_plugins)
        if qt_plugins_str not in current_qt_plugin_path:
            if current_qt_plugin_path:
                os.environ['QT_PLUGIN_PATH'] = qt_plugins_str + os.pathsep + current_qt_plugin_path
            else:
                os.environ['QT_PLUGIN_PATH'] = qt_plugins_str
    
    current_qt_qml_path = os.environ.get('QML2_IMPORT_PATH', '')
    if qt_qml.exists() and str(qt_qml) not in current_qt_qml_path:
        if current_qt_qml_path:
            os.environ['QML2_IMPORT_PATH'] = str(qt_qml) + os.pathsep + current_qt_qml_path
        else:
            os.environ['QML2_IMPORT_PATH'] = str(qt_qml)
    
    return True


setup_pyside6_env()


from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

try:
    from text_annotator.main_window import MainWindow
except ImportError:
    from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    
    app.setApplicationName("红墨文本标注工具")
    app.setApplicationDisplayName("红墨文本标注工具")
    app.setOrganizationName("RedInk")
    app.setOrganizationDomain("redink.example.com")
    
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    app.setStyle("Fusion")
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
