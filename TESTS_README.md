# 五子棋积分系统测试配置

## 快速开始

### Windows 批处理脚本
```batch
test_gobang_points.bat           # 运行所有测试
test_gobang_points.bat api       # 仅运行后端测试
test_gobang_points.bat frontend  # 仅运行前端测试
```

### 手动运行

#### 后端测试 (Django)
```bash
# 运行所有五子棋积分测试
./.conda/python.exe manage.py test EAW.tests.test_gobang_points

# 运行特定测试类
./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsAPITest

# 详细输出
./.conda/python.exe manage.py test EAW.tests.test_gobang_points --verbosity=2
```

#### 前端测试 (React)
```bash
cd external/gobang

# 运行所有测试
npm test

# 运行特定测试文件
npm test control.test.js

# 生成覆盖率报告
npm test -- --coverage

# 监视模式
npm test -- --watch
```

## 测试文件结构

```
EbbinghausAnywhere/
├── EAW/tests/
│   ├── test_gobang_points.py          # 后端API测试 (12个测试)
│   ├── test_gobang_static_files.py    # 静态文件测试
│   └── GOBANG_POINTS_TEST_REPORT.md   # 测试报告文档
├── external/gobang/src/components/
│   ├── control.js                     # 控制面板组件
│   └── control.test.js                # 前端组件测试
└── test_gobang_points.bat             # Windows测试脚本
```

## 测试覆盖

### 后端测试 (test_gobang_points.py)

| 测试类 | 测试数量 | 描述 |
|-------|---------|------|
| `GobangPointsAPITest` | 8 | API端点测试 |
| `GobangViewPointsIntegrationTest` | 2 | 视图集成测试 |
| `GobangPointsHistoryTest` | 2 | 历史记录测试 |
| **总计** | **12** | **全部通过** ✓ |

### 前端测试 (control.test.js)

| 测试组 | 描述 |
|-------|------|
| 基本渲染 | 组件渲染测试 |
| 开始按钮交互 | 确认对话框测试 |
| 积分扣除成功 | API调用测试 |
| 积分不足处理 | 错误处理测试 |
| 网络错误处理 | 异常处理测试 |
| 按钮状态 | 状态管理测试 |
| CSRF Token | 安全测试 |

## 测试结果

```bash
$ ./.conda/python.exe manage.py test EAW.tests.test_gobang_points

Found 12 test(s).
...
Ran 12 tests in 5.464s
OK
```

✅ 所有12个后端测试通过

## 测试数据

### 测试用户
- `testgobang` - 主要测试用户（100积分）
- `testview` - 页面测试用户（50积分）
- `testhistory` - 历史测试用户（100积分）

### 积分场景
| 场景 | 初始 | 需要 | 结果 |
|-----|------|-----|------|
| 正常 | 100 | 5 | ✓ 成功，剩余95 |
| 不足 | 3 | 5 | ✗ 失败，报错 |
| 零积分 | 0 | 5 | ✗ 失败，报错 |
| 边界 | 5 | 5 | ✓ 成功，剩余0 |
| 多局 | 100 | 15 | ✓ 成功，剩余85 |

## 常见问题

### Q: 测试失败怎么办？
A: 检查是否正确配置了测试数据库，Django会自动创建内存数据库。

### Q: 如何运行单个测试？
A: 使用完整路径：
```bash
./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsAPITest.test_start_game_deducts_5_points
```

### Q: 前端测试依赖问题？
A: 确保安装了测试依赖：
```bash
cd external/gobang
npm install --save-dev @testing-library/react @testing-library/jest-dom jest-fetch-mock
```

### Q: 如何调试测试？
A: 在测试代码中使用 `print()` 或 `pdb.set_trace()`（后端），或使用 `console.log()`（前端）。

## 相关文档

- [测试报告](EAW/tests/GOBANG_POINTS_TEST_REPORT.md)
- [积分系统设计](docs/积分商城/POINTS_SYSTEM_DESIGN.md)
- [PR文档](docs/PR文档/PR#9_Feat_积分系统.md)

## 维护

添加新功能时请同步更新测试用例，确保测试覆盖率。
