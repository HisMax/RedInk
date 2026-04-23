@echo off
chcp 65001 >nul
echo ========================================
echo    红墨文本标注工具 - RedInk Text Annotator
echo ========================================
echo.

cd /d "%~dp0"

echo 正在检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 正在检查依赖...
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 PySide6，正在安装...
    pip install PySide6 -q
    if errorlevel 1 (
        echo [错误] PySide6 安装失败
        pause
        exit /b 1
    )
    echo PySide6 安装成功
)

echo.
echo 正在启动应用程序...
echo.

python -m text_annotator.app

pause
