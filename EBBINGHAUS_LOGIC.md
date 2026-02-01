# 艾宾浩斯遗忘曲线复习系统逻辑文档

## 1. 基本概念

本系统基于艾宾浩斯遗忘曲线理论，通过科学的时间间隔安排复习，帮助用户有效记忆学习内容。

### 1.1 复习间隔设置

系统基于单词的创建日期预设9个复习间隔点（天数）：

```python
intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
```

对应的复习次数：
- Day 0 → 第1次复习（创建当天）
- Day 1 → 第2次复习（创建后第1天）
- Day 2 → 第3次复习（创建后第2天）
- Day 4 → 第4次复习（创建后第4天）
- Day 7 → 第5次复习（创建后第7天）
- Day 15 → 第6次复习（创建后第15天）
- Day 30 → 第7次复习（创建后第30天）
- Day 90 → 第8次复习（创建后第90天）
- Day 180 → 第9次复习（创建后第180天）

## 3. 复习逻辑详解

### 3.1 点击YES（记得）

#### 3.1.1 正式复习点YES
- **判断条件**：`next_review_date <= 当前选择日期`
- **执行操作**：
  1. 进入下一个间隔周期
  2. 计算新的 `next_review_date = 当前日期 + (下个间隔 - 当前间隔)`
  3. 清除额外复习标记：`needs_extra_review = False`, `extra_review_since = None`
  4. 清空不熟悉历史：`unfamiliar_history = []`
  5. 更新状态：`proficiency = MASTERED`

**计算示例**：
```
  2. **不改变** `current_interval` 和 `next_review_date`
  3. 等到正式复习日时再进入下一周期

### 3.2 点击NO（不记得）

#### 3.2.1 记录不熟悉
不管是正式复习还是额外复习，都会记录：
```python
current_cycle_count = sum(
    1 for record in unfamiliar_history 
    if record.get('interval') == current_interval
)
```

#### 3.2.3 判断是否达到3次
**达到3次（触发重置）**：
```python
if current_cycle_count >= 3:
    current_interval = 0           # 重置到Day 0
    next_review_date = 今天        # 从今天开始
    unfamiliar_history = []        # 清空历史
    needs_extra_review = False     # 清除额外复习
```

**未达到3次（继续当前周期）**：
- **正式复习日点NO**：
  ```python
  # 不改变 current_interval（保持在当前周期）
  # 不改变 next_review_date（下次正式复习日不变）
  needs_extra_review = True
  extra_review_since = 明天
  ```
  
- **额外复习点NO**：
  ```python
  # 所有字段保持不变
  # 继续额外复习状态
  ```

### 3.3 点击RESET（重置）

**确认后执行**：
```python
current_interval = 0
next_review_date = 今天
proficiency = UNFAMILIAR
unfamiliar_history = []
needs_extra_review = False
extra_review_since = None
```

## 4. 额外复习机制

### 4.1 触发条件
在正式复习日点NO后触发额外复习。

### 4.2 额外复习期间
- 从 `extra_review_since` 到 `next_review_date` 之间每天都会显示
- 单词会在复习列表中高亮显示（黄色背景）
- 显示"额外复习"或"常规+额外"标签

### 4.3 额外复习结束
- **点YES**：清除额外复习标记
- **到达正式复习日**：额外复习自动失效（查询条件排除）

## 5. 查询逻辑

### 5.1 显示条件
单词显示在复习列表的条件（满足其一）：
```python
Q(next_review_date <= 选择日期) |  # 正式复习日到了
Q(needs_extra_review=True, 
  extra_review_since <= 选择日期,
  next_review_date > 选择日期)     # 额外复习期间且未到正式日
```

### 5.2 复习类型判断
```python
is_regular = next_review_date <= 选择日期
is_extra = needs_extra_review=True and extra_review_since <= 选择日期 and next_review_date > 选择日期

# 三种状态：
# 1. is_regular=True, is_extra=False  → 常规复习
# 2. is_regular=False, is_extra=True  → 额外复习
# 3. is_regular=True, is_extra=True   → 常规+额外（不应该出现，查询已排除）
```

## 6. 完整场景示例

### 6.1 顺利通过场景
```
2月1日: 创建单词 → current_interval=0, next_review_date=2月1日
2月1日: 点YES    → current_interval=1, next_review_date=2月2日
2月2日: 点YES    → current_interval=2, next_review_date=2月3日
2月3日: 点YES    → current_interval=4, next_review_date=2月5日
2月5日: 点YES    → current_interval=7, next_review_date=2月8日
...依此类推
```

### 6.2 点NO触发额外复习场景
```
2月1日: Day 0点YES → current_interval=1, next_review_date=2月2日
2月2日: Day 1点NO  → 
        - 记录unfamiliar_history: {date:"2026-02-02", interval:1}
        - current_interval=1 (不变)
        - next_review_date=2月2日 (不变)
        - needs_extra_review=True, extra_review_since=2月3日
        - unfamiliar_count: 1/3

2月3日: 额外复习点NO →
        - 记录unfamiliar_history: {date:"2026-02-03", interval:1}
        - 所有字段保持不变
        - unfamiliar_count: 2/3

2月4日: 额外复习点YES →
        - 清除额外复习: needs_extra_review=False
        - current_interval=1, next_review_date=2月2日 (保持不变)
        - 等到2月2日（已过期）复习时才进入Day 2
```

### 6.3 3次不熟悉重置场景
```
2月1日: Day 1点NO  → unfamiliar_count: 1/3, 设置额外复习
2月2日: 额外复习NO → unfamiliar_count: 2/3
2月3日: 额外复习NO → unfamiliar_count: 3/3
        → 触发重置: current_interval=0, next_review_date=2月3日
        → 从Day 0重新开始
```

### 6.4 逾期复习场景
```
2月1日: Day 1, next_review_date=2月2日
2月5日: 用户才来复习（逾期3天）
        - 显示"逾期3天"标签
        - 点YES → next_review_date = 2月5日 + (2-1) = 2月6日
        - 进入Day 2
```

## 7. 界面显示说明

### 7.1 表格列说明

| 列名 | 说明 |
|------|------|
| Item | 单词/项目名称 |
| Category | 分类 |
| Review Cycle | 第N次复习（或"额外复习"） |
| Scheduled Review Date | 计划复习日期 + 逾期提示 |
| Next Review Date | 如果点YES，下次复习日期 |
| Unfamiliar | 不熟悉次数（X/3） |
| Review Type | 常规复习/额外复习/常规+额外 |
| Status | 待复习 |

### 7.2 颜色标记
- **常规复习**：蓝色标签
- **额外复习**：橙色标签，黄色行背景
- **常规+额外**：红色标签（理论上不应出现）
- **逾期**：红色"逾期X天"标签
- **不熟悉计数**：红色（有记录）/ 灰色（0次）

## 8. 关键设计原则

1. **日期驱动**：使用 `next_review_date` 而非计算方式，避免重复显示
2. **周期独立**：每个interval周期的不熟悉次数独立统计
3. **保持周期**：点NO不进入下一周期，保持当前周期直到点YES
4. **额外复习时限**：额外复习只在下次正式复习日之前有效
5. **3次重置**：同一周期内3次不熟悉触发重置，从Day 0重新开始
6. **历史清空**：点YES进入下一周期时清空不熟悉历史，重新计数

## 9. 注意事项

1. **proficiency字段**：只记录上次复习结果，不决定是否显示在复习列表
2. **日期选择**：用户可以选择任意日期进行复习（包括未来日期进行测试）
3. **逾期处理**：逾期不影响周期进度，点YES后继续正常进入下一周期
4. **自动跳转**：点YES/NO后自动跳转到下一个未复习单词
5. **内容刷新**：完成所有复习后自动刷新列表，更新日期信息

## 10. 技术实现要点

### 10.1 前端JavaScript
- 从日期选择器获取当前日期：`document.getElementById("id_review_date").value`
- AJAX请求时传递正确的复习日期
- 完成复习后调用 `loadReviewContent()` 刷新内容

### 10.2 后端计算
- 使用 Q 对象构建复杂查询条件
- 计算 `next_review_after_yes` 预测下次复习日期
- 在后端计算逾期天数、不熟悉次数等统计信息

### 10.3 数据库
- JSONField 存储不熟悉历史，支持复杂查询
- 日期字段使用 DateField，便于比较和计算
- 迁移文件：0010_item_current_interval_item_extra_review_since_and_more.py

---

**文档版本**：1.0  
**最后更新**：2026年2月1日  
**维护者**：EbbinghausAnywhere 开发团队
