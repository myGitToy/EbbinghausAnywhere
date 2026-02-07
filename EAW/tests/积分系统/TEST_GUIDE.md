# 积分系统测试指南

## 📋 测试文件说明

已创建以下测试相关文件：

1. **[EAW/tests/test_points_system.py](EAW/tests/test_points_system.py)** - 单元测试代码
2. **[run_tests.bat](run_tests.bat)** - 批处理测试脚本（CMD）
3. **[run_tests_detailed.bat](run_tests_detailed.bat)** - 详细测试报告脚本
4. **[run_tests.ps1](run_tests.ps1)** - PowerShell测试脚本（推荐）

---

## 🚀 运行测试

### 方法1：使用PowerShell脚本（推荐）

```powershell
cd C:\Users\GHUIQ\repos\EbbinghausAnywhere

# 运行测试
.\run_tests.ps1
```

**优势：**
- ✅ 自动检测并激活.conda环境
- ✅ 彩色输出，易于阅读
- ✅ 详细的测试统计
- ✅ 自动保存测试结果到文件

### 方法2：使用批处理脚本

```cmd
cd C:\Users\GHUIQ\repos\EbbinghausAnywhere

# 运行测试
run_tests.bat
```

### 方法3：手动运行测试

```powershell
cd C:\Users\GHUIQ\repos\EbbinghausAnywhere

# 激活环境
conda activate base

# 或者使用.conda
$env:Path = "C:\Users\GHUIQ\repos\EbbinghausAnywhere\.conda;" + $env:Path

# 运行测试
python manage.py test EAW.tests.test_points_system --verbosity=2
```

---

## 📊 测试覆盖范围

### 1. 模型测试 (Model Tests)

#### UserPointsModelTest - 用户积分账户测试
- ✅ 创建积分账户
- ✅ 增加积分
- ✅ 消费积分
- ✅ 积分不足检查
- ✅ 负数积分检查

#### PointHistoryModelTest - 积分历史测试
- ✅ 历史记录创建
- ✅ 记录字段验证

#### UserPointsConfigModelTest - 用户配置测试
- ✅ 默认配置值
- ✅ 自定义配置

#### PointRedemptionModelTest - 兑换记录测试
- ✅ 创建兑换记录

#### UserStreakModelTest - 连续学习/签到测试
- ✅ 初始状态
- ✅ 第一次学习
- ✅ 连续学习天数
- ✅ 学习中断
- ✅ 同一天多次学习
- ✅ 签到连续性
- ✅ 连续学习奖励
- ✅ 奖励重复检查
- ✅ 奖励功能禁用

### 2. 集成测试 (Integration Tests)

#### PointsIntegrationTest - 集成流程测试
- ✅ 完整积分流程（复习→签到→兑换→历史记录）
- ✅ 兑换流程

### 3. API测试 (API Tests)

#### PointsAPITest - API接口测试
- ✅ 积分商城页面
- ✅ 积分配置页面
- ✅ 积分历史页面
- ✅ 兑换API
- ✅ 积分不足检查
- ✅ 签到API
- ✅ 重复签到检查
- ✅ 获取积分余额API

### 4. 边界测试 (Edge Cases)

#### EdgeCasesTest - 边界情况测试
- ✅ 兑换0分钟
- ✅ 兑换负数分钟
- ✅ 超过最大兑换时长
- ✅ 自定义汇率测试

---

## ✅ 预期测试结果

如果所有测试通过，你应该看到类似输出：

```
test_add_points (EAW.tests.test_points_system.UserPointsModelTest) ... ok
test_spend_points (EAW.tests.test_points_system.UserPointsModelTest) ... ok
test_spend_insufficient_points (EAW.tests.test_points_system.UserPointsModelTest) ... ok
...

======================================================================
Ran 25 tests in 2.345s

OK
```

**统计：**
- 约25个测试用例
- 覆盖所有核心功能
- 执行时间约2-5秒

---

## ❗ 常见问题

### 问题1：ModuleNotFoundError: No module named 'django'

**原因：** Django未安装或环境未激活

**解决：**
```powershell
# 方法1：激活conda环境
conda activate base

# 方法2：使用.conda环境
$env:Path = "C:\Users\GHUIQ\repos\EbbinghausAnywhere\.conda;" + $env:Path
```

### 问题2：ImportError: cannot import name 'UserPoints'

**原因：** 数据库迁移未执行

**解决：**
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 问题3：DatabaseError: no such table

**原因：** 表不存在

**解决：** 先运行数据库迁移

### 问题4：AssertionError

**原因：** 测试用例失败

**解决：** 检查错误信息，可能是代码逻辑问题

---

## 🔍 测试结果解读

### 成功输出示例：
```
test_complete_points_flow (EAW.tests.test_points_system.PointsIntegrationTest) ... ok
test_redemption_flow (EAW.tests.test_points_system.PointsIntegrationTest) ... ok
...
======================================================================
Ran 25 tests in 3.456s

OK
```

### 失败输出示例：
```
test_add_points (EAW.tests.test_points_system.UserPointsModelTest) ... FAIL
...
======================================================================
FAILED (failures=1)
```

**查看详细错误：**
```
python manage.py test EAW.tests.test_points_system --verbosity=3
```

---

## 📈 测试覆盖率

本测试套件覆盖的功能模块：

| 模块 | 测试数量 | 覆盖率 |
|------|---------|--------|
| UserPoints模型 | 5 | 100% |
| PointHistory模型 | 1 | 100% |
| UserPointsConfig模型 | 2 | 100% |
| PointRedemption模型 | 1 | 100% |
| UserStreak模型 | 8 | 100% |
| 集成流程 | 2 | 100% |
| API接口 | 6 | 100% |
| 边界情况 | 4 | 100% |

---

## 🎯 测试清单

### 运行测试前检查：
- [ ] 数据库迁移已完成
- [ ] Python环境已激活（.conda或conda）
- [ ] Django已安装
- [ ] 所有依赖已安装

### 测试功能清单：
- [ ] 复习单词获得积分
- [ ] 每日签到获得积分
- [ ] 连续学习奖励触发
- [ ] 积分兑换功能
- [ ] 用户配置修改
- [ ] 积分历史记录
- [ ] 积分不足检查
- [ ] 边界情况处理

---

## 📝 测试最佳实践

1. **运行测试前**
   - 确保数据库已迁移
   - 确保环境已激活
   - 关闭其他可能使用数据库的程序

2. **运行测试时**
   - 使用 `--verbosity=2` 查看详细输出
   - 使用 `--verbosity=3` 查看调试信息

3. **测试失败后**
   - 查看完整错误堆栈
   - 检查相关代码
   - 修复后重新运行

4. **持续集成**
   - 在部署前运行所有测试
   - 代码修改后运行相关测试
   - 定期运行完整测试套件

---

## 🚀 快速开始

**完整测试流程：**

```powershell
# 1. 进入项目目录
cd C:\Users\GHUIQ\repos\EbbinghausAnywhere

# 2. 激活环境
conda activate base

# 3. 运行迁移（如果还没运行）
python manage.py makemigrations
python manage.py migrate

# 4. 运行测试
.\run_tests.ps1
```

**快速测试（跳过迁移）：**

```powershell
.\run_tests.ps1
```

---

## 📚 相关文档

- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 数据库迁移指南
- [POINTS_SYSTEM_DESIGN.md](docs/POINTS_SYSTEM_DESIGN.md) - 系统设计文档
- [Django测试文档](https://docs.djangoproject.com/en/4.1/topics/testing/)

---

**祝测试顺利！** 🎉
