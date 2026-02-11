@echo off
REM 五子棋积分系统测试运行脚本
REM
REM 用法:
REM   test_gobang_points.bat           - 运行所有测试
REM   test_gobang_points.bat api       - 仅运行后端API测试
REM   test_gobang_points.bat frontend  - 仅运行前端测试

setlocal

set PYTHON_EXE=.conda\python.exe
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

if "%1"=="api" (
    echo ========================================
    echo 运行五子棋积分系统后端测试
    echo ========================================
    %PYTHON_EXE% manage.py test EAW.tests.test_gobang_points --verbosity=2
) else if "%1"=="frontend" (
    echo ========================================
    echo 运行五子棋前端组件测试
    echo ========================================
    cd external\gobang
    call npm test -- control.test.js
    cd /d "%PROJECT_DIR%"
) else (
    echo ========================================
    echo 运行所有五子棋积分系统测试
    echo ========================================
    echo.
    echo [1/2] 运行后端测试...
    %PYTHON_EXE% manage.py test EAW.tests.test_gobang_points --verbosity=2
    if %ERRORLEVEL% neq 0 (
        echo 后端测试失败！
        pause
        exit /b 1
    )
    echo.
    echo [2/2] 运行前端测试...
    cd external\gobang
    call npm test -- control.test.js
    cd /d "%PROJECT_DIR%"
)

echo.
echo ========================================
echo 测试完成！
echo ========================================
pause
