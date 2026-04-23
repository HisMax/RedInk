import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
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
