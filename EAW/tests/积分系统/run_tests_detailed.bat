@echo off
chcp 65001 >nul
REM ========================================
REM 积分系统详细测试报告脚本
REM ========================================

echo.
echo ========================================
echo  积分系统详细测试报告
echo ========================================
echo.

cd /d "%~dp0"

REM 检测并激活环境
if exist .conda\python.exe (
    echo ✓ 使用 .conda 环境
    set "PATH=%CD%\.conda;%CD%\.conda\Scripts;%PATH%"
) else if exist .venv\Scripts\python.exe (
    echo ✓ 使用 .venv 环境
    call .venv\Scripts\activate.bat
) else (
    where conda >nul 2>&1
    if %errorlevel% equ 0 (
        call conda activate base
    )
)

echo.
echo ========================================
echo  开始测试...
echo ========================================
echo.

REM 创建测试结果文件
set RESULT_FILE=test_results_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.txt
set RESULT_FILE=%RESULT_FILE: =0%

echo 测试开始时间: %date% %time% > %RESULT_FILE%
echo. >> %RESULT_FILE%

REM 运行测试并保存结果
python manage.py test EAW.tests.test_points_system --verbosity=2 >> %RESULT_FILE% 2>&1

echo.
echo 测试结束时间: %date% %time% >> %RESULT_FILE%

REM 显示测试结果摘要
echo.
echo ========================================
echo  测试结果摘要
echo ========================================
echo.

python -c "import re; content = open('%RESULT_FILE%', 'r', encoding='utf-8').read(); failures = re.findall(r'FAILED|ERROR', content); success = re.findall(r'^OK|FAILED', content, re.MULTILINE); print(f'找到的错误: {len(failures)}'); print(f'测试结果: {len(success)}')" 2>nul

echo.
echo 详细结果已保存到: %RESULT_FILE%
echo.
echo 是否打开详细测试报告？ (Y/N)
choice /c Y /n /m "Y=是, N=否" /t 5, default Y
if errorlevel 2 goto :end
if errorlevel 1 goto :end

type %RESULT_FILE% | more

:end
echo.
echo ========================================
echo  测试报告完成
echo ========================================
echo.

pause
