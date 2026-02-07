@echo off
chcp 65001 >nul
REM ========================================
REM 积分系统自动化测试脚本
REM ========================================

echo.
echo ========================================
echo  积分系统自动化测试
echo ========================================
echo.

cd /d "%~dp0"

echo [步骤 1/3] 检测Python环境...
echo.

REM 优先检查项目目录下的.conda环境
if exist .conda\python.exe (
    echo ✓ 找到项目本地的 .conda 环境
    set "PATH=%CD%\.conda;%CD%\.conda\Scripts;%PATH%"
    goto :run_tests
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
        goto :run_tests
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
    goto :run_tests
)

if exist venv\Scripts\python.exe (
    echo ✓ 找到 venv 虚拟环境
    echo 正在激活虚拟环境...
    call venv\Scripts\activate.bat
    goto :run_tests
)

REM 检查系统Python
where python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 使用系统Python
    goto :run_tests
)

echo 错误: 未找到Python环境！
echo.
echo 请手动执行以下命令之一：
echo.
echo 1. Conda环境：
echo    conda activate base
echo    python manage.py test EAW.tests.test_points_system
echo.
echo 2. 或使用.conda环境：
echo    .\.conda\python.exe manage.py test EAW.tests.test_points_system
echo.
pause
exit /b 1

:run_tests
echo [步骤 2/3] 验证Django和依赖...
echo.
python -c "import django; print('Django版本:', django.get_version())" >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Django未安装！
    echo 正在安装Django...
    pip install django
)

echo [步骤 3/3] 运行积分系统测试...
echo.
echo ========================================
echo  测试类别：
echo  1. 用户积分账户模型测试
echo  2. 积分历史记录测试
echo  3. 用户配置测试
echo  4. 兑换记录测试
echo  5. 连续学习/签到逻辑测试
echo  6. 集成流程测试
echo  7. API接口测试
echo  8. 边界情况测试
echo ========================================
echo.

python manage.py test EAW.tests.test_points_system --verbosity=2

echo.
echo ========================================
echo  测试完成
echo ========================================
echo.
echo 如果测试通过，说明积分系统功能正常！
echo 如果有失败，请检查上面的错误信息。
echo.

pause
