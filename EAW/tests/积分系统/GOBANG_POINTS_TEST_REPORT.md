# 五子棋积分系统测试报告

## 测试概述

本文档描述了五子棋游戏积分扣除功能的完整测试套件，包括后端API测试和前端组件测试。

## 测试文件结构

```
EbbinghausAnywhere/
├── EAW/
│   ├── tests/
│   │   └── test_gobang_points.py          # 后端API测试
│   ├── views.py                          # gobang_start_game_api 视图
│   └── urls.py                           # /api/gobang/start/ 路由
└── external/
    └── gobang/
        └── src/
            └── components/
                ├── control.js             # 控制面板组件
                └── control.test.js        # 前端组件测试
```

## 后端测试 (test_gobang_points.py)

### 测试类：`GobangPointsAPITest`

#### 测试用例列表

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| `test_start_game_api_requires_login` | API访问控制 | 未登录用户无法调用API |
| `test_start_game_deducts_5_points` | 基础积分扣除 | 成功扣除5积分 |
| `test_start_game_with_insufficient_points` | 积分不足处理 | 返回错误信息，不扣除积分 |
| `test_start_game_creates_history_record` | 历史记录创建 | 创建PointHistory记录 |
| `test_start_game_response_includes_remaining_points` | 响应格式 | 包含剩余积分信息 |
| `test_multiple_games_deduct_multiple_times` | 多局游戏 | 多次扣除积分正确 |
| `test_start_game_with_zero_points` | 零积分处理 | 积分为0时拒绝开始 |
| `test_start_game_with_exactly_5_points` | 边界测试 | 刚好5积分可以开始 |

### 测试类：`GobangViewPointsIntegrationTest`

#### 测试用例列表

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| `test_gobang_page_shows_remaining_points` | 页面显示积分 | 上下文包含剩余积分 |
| `test_gobang_page_creates_points_account_if_not_exists` | 自动创建账户 | 首次访问自动创建积分账户 |

### 测试类：`GobangPointsHistoryTest`

#### 测试用例列表

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| `test_game_history_has_reference_id` | 参考ID格式 | 包含gobang_前缀 |
| `test_multiple_games_create_unique_reference_ids` | 唯一性 | 每局游戏ID唯一 |

## 前端测试 (control.test.js)

### 测试组：基本渲染

| 测试用例 | 描述 |
|---------|------|
| 组件正常渲染 | 渲染开始、悔棋、认输按钮 |

### 测试组：开始按钮交互

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| 显示确认对话框 | 点击开始显示积分确认弹窗 |
| 取消操作 | 点击取消关闭对话框 |

### 测试组：积分扣除成功

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| API调用成功 | 调用 /api/gobang/start/ |
| 关闭对话框 | 成功后关闭确认弹窗 |
| CSRF Token | 请求包含CSRF token |

### 测试组：积分不足处理

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| 错误提示显示 | 显示"积分不足"错误 |
| 不开始游戏 | 不调用startGame action |

### 测试组：网络错误处理

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| 网络错误提示 | 显示"无法连接到服务器" |

### 测试组：按钮状态

| 测试用例 | 描述 | 验证点 |
|---------|------|--------|
| 游戏进行中禁用 | gaming状态下开始按钮禁用 |
| 加载中禁用 | loading状态下开始按钮禁用 |
| 确认按钮加载状态 | API调用时显示loading |

## 运行测试

### 后端测试

```bash
# 运行所有五子棋积分测试
./.conda/python.exe manage.py test EAW.tests.test_gobang_points

# 运行特定测试类
./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsAPITest

# 运行单个测试用例
./.conda/python.exe manage.py test EAW.tests.test_gobang_points.GobangPointsAPITest.test_start_game_deducts_5_points

# 带详细输出
./.conda/python.exe manage.py test EAW.tests.test_gobang_points --verbosity=2
```

### 前端测试

```bash
cd external/gobang

# 安装测试依赖（如果还没有）
npm install --save-dev @testing-library/react @testing-library/jest-dom jest-fetch-mock

# 运行所有测试
npm test

# 运行特定测试文件
npm test control.test.js

# 运行测试并生成覆盖率报告
npm test -- --coverage

# 监视模式
npm test -- --watch
```

## 测试数据

### 测试用户

后端测试自动创建以下测试用户：

- `testgobang` - 主要测试用户，初始积分100
- `testview` - 页面集成测试用户，初始积分50
- `testhistory` - 历史记录测试用户，初始积分100
- `newuser` - 新用户测试，无初始积分

### 积分场景

| 场景 | 初始积分 | 需要积分 | 结果 |
|-----|---------|---------|------|
| 正常情况 | 100 | 5 | 成功，剩余95 |
| 积分不足 | 3 | 5 | 失败，返回错误 |
| 零积分 | 0 | 5 | 失败，返回错误 |
| 边界情况 | 5 | 5 | 成功，剩余0 |
| 多局游戏 | 100 | 15 (3局) | 成功，剩余85 |

## API规范

### 开始游戏 API

**端点:** `POST /api/gobang/start/`

**请求头:**
```
Content-Type: application/json
X-CSRFToken: <csrftoken>
```

**请求体:**
```json
{}
```

**成功响应 (200 OK):**
```json
{
  "success": true,
  "message": "开始游戏成功！扣除5积分",
  "remaining_points": 95
}
```

**失败响应 (200 OK):**
```json
{
  "success": false,
  "message": "积分不足！开始游戏需要5积分，当前3积分"
}
```

## 集成测试清单

- [x] 后端API测试
  - [x] 访问控制测试
  - [x] 积分扣除逻辑测试
  - [x] 积分不足处理测试
  - [x] 历史记录测试
  - [x] 边界情况测试
- [x] 前端组件测试
  - [x] 组件渲染测试
  - [x] 用户交互测试
  - [x] API调用测试
  - [x] 错误处理测试
  - [x] 状态管理测试
- [x] 集成测试
  - [x] 前后端联调测试
  - [x] 完整用户流程测试

## 注意事项

1. **测试数据库**: 测试使用独立的数据库，不会影响生产数据
2. **CSRF保护**: 前端测试需要mock CSRF token
3. **异步操作**: 使用 `waitFor` 处理异步状态更新
4. **Mock策略**: 后端测试不需要mock，前端测试需要mock fetch API

## 维护建议

1. **添加新功能时**: 同时添加对应的测试用例
2. **修改API响应格式**: 更新测试中的预期响应
3. **增加积分规则**: 更新边界测试
4. **修改UI流程**: 更新前端交互测试

## 相关文档

- [积分系统设计文档](../docs/积分商城/POINTS_SYSTEM_DESIGN.md)
- [五子棋静态文件测试](./test_gobang_static_files.py)
- [积分系统测试](./test_points_system.py)
