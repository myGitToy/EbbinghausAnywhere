# 积分系统自动化测试脚本 (PowerShell版本)
# 使用方法: 在PowerShell中运行 .\run_tests.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 积分系统自动化测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 进入项目目录
$ProjectRoot = "C:\Users\GHUIQ\repos\EbbinghausAnywhere"
Set-Location $ProjectRoot

# 步骤1：检测并激活Python环境
Write-Host "[步骤 1/3] 检测Python环境..." -ForegroundColor Yellow
Write-Host ""

$PythonFound = $false

# 优先使用.conda环境
if (Test-Path ".conda\python.exe") {
    Write-Host "✓ 找到项目本地的 .conda 环境" -ForegroundColor Green
    $env:Path = "$ProjectRoot\.conda;$ProjectRoot\.conda\Scripts;" + $env:Path
    $PythonFound = $true
}
# 检查.venv
elseif (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "✓ 找到 .venv 虚拟环境" -ForegroundColor Green
    & ".\.venv\Scripts\Activate.ps1"
    $PythonFound = $true
}
# 检查venv
elseif (Test-Path "venv\Scripts\python.exe") {
    Write-Host "✓ 找到 venv 虚拟环境" -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
    $PythonFound = $true
}
# 尝试使用conda
elseif (Get-Command conda -ErrorAction SilentlyContinue) {
    Write-Host "✓ 找到Conda，正在激活base环境..." -ForegroundColor Green
    conda activate base
    $PythonFound = $true
}

if (-not $PythonFound) {
    Write-Host "错误: 未找到Python环境！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动激活环境后再运行测试" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 步骤2：验证Django
Write-Host "[步骤 2/3] 验证Django安装..." -ForegroundColor Yellow
Write-Host ""

try {
    $djangoVersion = python -c "import django; print(django.get_version())" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Django版本: $djangoVersion" -ForegroundColor Green
    } else {
        throw "Django导入失败"
    }
} catch {
    Write-Host "正在安装Django..." -ForegroundColor Yellow
    pip install django
}

Write-Host ""

# 步骤3：运行测试
Write-Host "[步骤 3/3] 运行积分系统测试..." -ForegroundColor Yellow
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "测试类别：" -ForegroundColor Cyan
Write-Host "1. 用户积分账户模型测试" -ForegroundColor White
Write-Host "2. 积分历史记录测试" -ForegroundColor White
Write-Host "3. 用户配置测试" -ForegroundColor White
Write-Host "4. 兑换记录测试" -ForegroundColor White
Write-Host "5. 连续学习/签到逻辑测试" -ForegroundColor White
Write-Host "6. 集成流程测试" -ForegroundColor White
Write-Host "7. API接口测试" -ForegroundColor White
Write-Host "8. 边界情况测试" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$TestResultFile = "test_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

Write-Host "测试开始: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

# 运行测试并捕获输出
$TestOutput = python manage.py test EAW.tests.test_points_system --verbosity=2 2>&1
$TestExitCode = $LASTEXITCODE

# 保存结果
$TestOutput | Out-File -FilePath $TestResultFile -Encoding UTF8

# 显示结果
Write-Host "测试结束: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

if ($TestExitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ 所有测试通过！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green

    # 统计测试数量
    $OKCount = ($TestOutput | Select-String -Pattern "test_.*\(.*\).*ok" | Measure-Object).Count
    $DotCount = ($TestOutput | Select-String -Pattern "\.{2,}" | Measure-Object).Count / 2

    Write-Host ""
    Write-Host "测试统计:" -ForegroundColor Cyan
    Write-Host "- 测试用例: $DotCount" -ForegroundColor White
    Write-Host "- 成功: $OKCount" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ 部分测试失败" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red

    # 显示失败信息
    $FailedTests = $TestOutput | Select-String -Pattern "FAIL|ERROR|AssertionError" -Context 0, 2
    if ($FailedTests) {
        Write-Host ""
        Write-Host "失败的测试:" -ForegroundColor Yellow
        $FailedTests | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "详细结果已保存到: $TestResultFile" -ForegroundColor Cyan
Write-Host ""

# 询问是否查看详细结果
$Response = Read-Host "是否查看详细测试报告？(Y/N)"
if ($Response -eq 'Y' -or $Response -eq 'y') {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "详细测试报告" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Get-Content $TestResultFile | Select-Object -First 50
    Write-Host ""
    Write-Host "..." -ForegroundColor Gray
    Write-Host ""
    Get-Content $TestResultFile | Select-Object -Last 20
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "测试完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "如果测试全部通过，积分系统已准备就绪！" -ForegroundColor Green
Write-Host ""
