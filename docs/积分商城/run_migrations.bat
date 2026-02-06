@echo off
chcp 65001 >nul
REM ========================================
REM Ebbinghaus Anywhere - 数据库迁移脚本
REM 支持 Conda 环境检测
REM ========================================

echo.
echo ========================================
echo  Ebbinghaus Anywhere - 数据库迁移
echo ========================================
echo.

cd /d "%~dp0"

echo [步骤 1/4] 检测Python环境...
echo.

REM 检查是否在Conda环境中
if defined CONDA_PREFIX (
    echo ✓ 检测到Conda环境: %CONDA_PREFIX%
    echo ✓ 当前Python:
    python --version
    echo.
    goto :run_migrations
)

REM 优先检查项目目录下的.conda环境
if exist .conda\python.exe (
    echo ✓ 找到项目本地的 .conda 环境
    echo.
    echo 正在激活 .conda 环境...
    set "PATH=%CD%\.conda;%CD%\.conda\Scripts;%PATH%"
    goto :run_migrations
)

REM 检查Conda是否可用
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 找到Conda
    echo.
    echo 正在激活Conda base环境...
    call conda activate base
    if %errorlevel% equ 0 (
        echo ✓ Conda base环境已激活
        echo.
        goto :run_migrations
    ) else (
        echo 警告: 无法激活Conda环境，将尝试使用系统Python
        echo.
    )
)

REM 检查虚拟环境
if exist .venv\Scripts\python.exe (
    echo ✓ 找到 .venv 虚拟环境
    echo 正在激活虚拟环境...
    call .venv\Scripts\activate.bat
    goto :run_migrations
)

if exist venv\Scripts\python.exe (
    echo ✓ 找到 venv 虚拟环境
    echo 正在激活虚拟环境...
    call venv\Scripts\activate.bat
    goto :run_migrations
)

REM 检查系统Python
where python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 使用系统Python
    goto :run_migrations
)

echo 错误: 未找到Python环境！
echo.
echo 请手动执行以下命令之一：
echo.
echo 1. Conda环境：
echo    conda activate base
echo    python manage.py makemigrations
echo    python manage.py migrate
echo.
echo 2. 或直接使用Conda的Python：
echo    C:\Users\GHUIQ\.conda\python.exe manage.py makemigrations
echo    C:\Users\GHUIQ\.conda\python.exe manage.py migrate
echo.
pause
exit /b 1

:run_migrations
echo [步骤 2/4] 验证Django安装...
echo.
python -c "import django; print('Django版本:', django.get_version())" >nul 2>&1
if %errorlevel% neq 0 (
    echo Django未安装或无法导入，正在安装...
    pip install django
    if %errorlevel% neq 0 (
        echo.
        echo 错误: Django安装失败！
        pause
        exit /b 1
    )
    echo ✓ Django安装成功
) else (
    echo ✓ Django已安装
)
echo.

echo [步骤 3/4] 创建数据库迁移文件...
echo 正在运行: python manage.py makemigrations
echo.
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo.
    echo 错误: makemigrations 失败！
    echo 请检查上面的错误信息。
    echo.
    pause
    exit /b 1
)
echo.
echo ✓ makemigrations 成功完成！
echo.

echo [步骤 4/4] 应用数据库迁移...
echo 正在运行: python manage.py migrate
echo.
python manage.py migrate
if %errorlevel% neq 0 (
    echo.
    echo 错误: migrate 失败！
    echo 请检查上面的错误信息。
    echo.
    pause
    exit /b 1
)
echo.
echo ✓ migrate 成功完成！
echo.

echo ========================================
echo  所有迁移步骤已成功完成！
echo ========================================
echo.
echo 下一步操作：
echo   保持当前环境激活，然后运行：
echo   python manage.py runserver
echo.
echo 访问测试页面：
echo   积分商城: http://localhost:8000/points/market/
echo   积分配置: http://localhost:8000/points/config/
echo   积分历史: http://localhost:8000/points/history/
echo   Admin后台: http://localhost:8000/admin/
echo.

pause
