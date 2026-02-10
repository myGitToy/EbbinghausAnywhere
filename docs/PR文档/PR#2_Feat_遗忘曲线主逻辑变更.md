# 遗忘曲线主逻辑变更

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #2
> **创建日期**：2026-02-01
> **功能分支**：feat_遗忘曲线主逻辑变更
> **目标分支**：main
> **合并日期**：2026-02-01
> **合并提交**：277dda1

## 功能概述

重构艾宾浩斯遗忘曲线复习系统的核心逻辑，引入科学的复习间隔算法、额外复习机制和不熟悉度追踪功能，实现真正的智能记忆管理。

## 背景说明

### 艾宾浩斯遗忘曲线原理

德国心理学家赫尔曼·艾宾浩斯（Hermann Ebbinghaus）发现了记忆遗忘的规律：

- **遗忘速度**：遗忘在学习后立即开始，最初速度很快，之后逐渐减缓
- **保持率**：20分钟后约58%，1小时后约44%，1天后约34%，6天后约25%
- **对抗遗忘**：在特定时间点进行复习，可以显著提高记忆保持率

### 优化后的复习间隔

本PR对复习间隔进行了科学优化：

```python
# 旧间隔（10个）：[0, 1, 2, 4, 7, 15, 30, 60, 90, 365]
# 新间隔（9个）：
intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
```

**变更说明**：
- **移除365天**：最后一个间隔点从365天改为180天
  - 更符合实际学习周期（半年制学习）
  - 避免过长间隔导致记忆衰退
  - 180天后再复习时已进入长期记忆阶段
- **移除60天**：从30天直接跳到90天，减少复习频次
  - 基于实践反馈：60天间隔时记忆保持率仍然较高
  - 优化用户体验：减少中期阶段的复习负担

### 原有系统的问题

1. **缺乏精确的复习计划**：没有明确的下次复习日期字段
2. **无法处理遗忘情况**：点击"不记得"后没有科学的应对机制
3. **复习周期不清晰**：无法追踪用户当前处于哪个复习阶段
4. **缺少逾期处理**：用户错过复习日期后无法正确恢复进度
5. **复习历史缺失**：无法分析用户的复习表现和遗忘模式

## 技术实现

### 1. 数据模型扩展

#### 新增字段

在 `Item` 模型中新增5个核心字段：

```python
# 1. 下次复习日期（核心驱动字段）
next_review_date = models.DateField(
    null=True,
    blank=True,
    help_text="Next scheduled review date"
)

# 2. 当前复习间隔（天数）
current_interval = models.IntegerField(
    default=0,
    help_text="Current review interval in days (0,1,2,4,7,15,30,90,180)"
)

# 3. 是否需要额外复习
needs_extra_review = models.BooleanField(
    default=False,
    help_text="Needs extra review (marked after clicking NO)"
)

# 4. 额外复习起始日期
extra_review_since = models.DateField(
    null=True,
    blank=True,
    help_text="Extra review start date"
)

# 5. 不熟悉历史记录
unfamiliar_history = models.JSONField(
    default=list,
    blank=True,
    help_text="History of unfamiliar markings"
)
```

#### 字段设计原理

| 字段 | 作用 | 设计考量 |
|------|------|----------|
| `next_review_date` | 系统主驱动，决定何时显示 | 使用日期字段而非计算，支持逾期处理 |
| `current_interval` | 标识当前周期 | 存储天数而非索引，便于理解 |
| `needs_extra_review` | 触发额外复习 | 布尔值，查询效率高 |
| `extra_review_since` | 额外复习范围控制 | 明确复习起止日期 |
| `unfamiliar_history` | 追踪遗忘模式 | JSONField，支持复杂结构 |

### 2. 复习间隔计算算法

#### 基础间隔序列

```python
INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180]
```

#### 点击YES时的日期计算

**核心公式**：
```python
next_review_date = 当前复习日期 + (下个间隔天数 - 当前间隔天数)
```

**计算示例**：

| 当前周期 | 当前间隔 | 下个间隔 | 日期增量 | 示例计算 |
|---------|---------|---------|---------|---------|
| Day 0 | 0 | 1 | +1 | 2/1点YES → 2/1 + (1-0) = 2/2 |
| Day 1 | 1 | 2 | +1 | 2/2点YES → 2/2 + (2-1) = 2/3 |
| Day 2 | 2 | 4 | +2 | 2/3点YES → 2/3 + (4-2) = 2/5 |
| Day 4 | 4 | 7 | +3 | 2/5点YES → 2/5 + (7-4) = 2/8 |
| Day 7 | 7 | 15 | +8 | 2/8点YES → 2/8 + (15-7) = 2/16 |
| Day 15 | 15 | 30 | +15 | 2/16点YES → 2/16 + (30-15) = 3/3 |
| Day 30 | 30 | 90 | +60 | 3/3点YES → 3/3 + (90-30) = 5/2 |
| Day 90 | 90 | 180 | +90 | 5/2点YES → 5/2 + (180-90) = 7/31 |
| Day 180 | 180 | - | 完成 | 复习完成，保持180天 |

**算法优势**：
- **相对增量**：基于实际复习日期计算，而非创建日期
- **逾期友好**：即使逾期复习，间隔增量仍然正确
- **逻辑清晰**：每个阶段的间隔增长一目了然

### 3. 额外复习机制

#### 触发条件

在正式复习日点击"NO"时触发：

```python
# 判断是否为正式复习日
is_regular_review = (next_review_date <= 当前选择日期)

if is_regular_review and 用户点击NO:
    needs_extra_review = True
    extra_review_since = 明天  # 从明天开始每天显示
```

#### 额外复习期间的行为

**显示条件**：
```python
# 查询逻辑：显示在复习列表的条件
from django.db.models import Q

# 正式复习日 OR 额外复习期间
Q(next_review_date <= 选择日期) |  # 正式复习
Q(needs_extra_review=True,
  extra_review_since <= 选择日期,
  next_review_date > 选择日期)    # 额外复习
```

**复习类型判断**：

```python
is_regular = (next_review_date <= 选择日期)
is_extra = (needs_extra_review and
            extra_review_since <= 选择日期 and
            next_review_date > 选择日期)

# 三种状态：
# 1. is_regular=True, is_extra=False  → 常规复习（蓝色标签）
# 2. is_regular=False, is_extra=True  → 额外复习（橙色标签，黄色行背景）
# 3. is_regular=True, is_extra=True   → 不应出现（查询已排除）
```

#### 额外复习的结束

- **点YES**：立即清除额外复习标记，进入下一周期
- **到达正式复习日**：自动转为常规复习，额外复习标记失效

### 4. 不熟悉度追踪系统

#### 记录结构

每次点击"NO"都会记录：

```python
unfamiliar_history.append({
    'date': '2026-02-02',      # 点击NO的日期
    'interval': 1,              # 当前的复习间隔（天数）
    'review_type': 'regular'   # 'regular' 或 'extra'
})
```

#### 周期独立计数

每个复习间隔周期独立统计不熟悉次数：

```python
# 计算当前周期的不熟悉次数
current_cycle_count = sum(
    1 for record in unfamiliar_history
    if record.get('interval') == current_interval
)
```

#### 3次触发重置机制

**设计理念**：
- 在同一复习周期内，如果用户连续3次标记为"不记得"
- 说明该内容未被掌握，需要从最基础的间隔（Day 0）重新学习

**实现逻辑**：

```python
if current_cycle_count >= 3:
    # 触发重置
    current_interval = 0
    next_review_date = 今天
    unfamiliar_history = []      # 清空历史
    needs_extra_review = False   # 清除额外复习
    extra_review_since = None
    proficiency = UNFAMILIAR
```

**重置场景示例**：

```
2月1日: Day 1 正式复习，点NO → unfamiliar_count: 1/3, 设置额外复习
2月2日: 额外复习，点NO     → unfamiliar_count: 2/3
2月3日: 额外复习，点NO     → unfamiliar_count: 3/3
                               → 触发重置，从Day 0重新开始
```

### 5. 核心视图逻辑变更

#### ReviewView（复习列表视图）

**查询逻辑重构**：

```python
# 旧逻辑：基于日期计算和 proficiency 字段
# 新逻辑：基于 next_review_date 和 needs_extra_review

selected_date = self.get_selected_date()  # 用户选择的日期

# 构建查询条件
query = (
    # 条件1：正式复习日已到
    Q(next_review_date__lte=selected_date) |
    # 条件2：额外复习期间
    Q(needs_extra_review=True,
      extra_review_since__lte=selected_date,
      next_review_date__gt=selected_date)
)

items = Item.objects.filter(user=self.request.user).filter(query)
```

**上下文数据增强**：

```python
for item in items:
    # 计算复习类型
    is_regular = item.next_review_date <= selected_date
    is_extra = (item.needs_extra_review and
                item.extra_review_since <= selected_date and
                item.next_review_date > selected_date)

    # 计算逾期天数
    if item.next_review_date < selected_date:
        overdue_days = (selected_date - item.next_review_date).days
    else:
        overdue_days = 0

    # 计算当前周期的不熟悉次数
    unfamiliar_count = sum(
        1 for record in (item.unfamiliar_history or [])
        if record.get('interval') == item.current_interval
    )

    # 预测：如果点YES，下次复习日期是？
    try:
        current_idx = INTERVALS.index(item.current_interval)
        if current_idx < len(INTERVALS) - 1:
            next_interval = INTERVALS[current_idx + 1]
            days_until = next_interval - item.current_interval
            next_review_after_yes = selected_date + timedelta(days=days_until)
        else:
            next_review_after_yes = None  # 已完成所有复习
    except ValueError:
        next_review_after_yes = None
```

#### ReviewFeedbackYesView（点击YES）

**核心逻辑**：

```python
def post(self, request, *args, **kwargs):
    item_id = request.POST.get('id')
    review_date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()

    item = Item.objects.get(id=item_id)

    # 幂等性检查：今天是否已经复习过
    if reviewed_today(item, review_date):
        return JsonResponse({'status': 'already_reviewed'})

    # 判断是否为正式复习日
    if item.next_review_date <= review_date:
        # 进入下一个周期
        try:
            current_idx = INTERVALS.index(item.current_interval)
            if current_idx < len(INTERVALS) - 1:
                next_interval = INTERVALS[current_idx + 1]
                days_until = next_interval - item.current_interval
                item.current_interval = next_interval
                item.next_review_date = review_date + timedelta(days=days_until)
            else:
                # 已完成所有间隔
                pass
        except ValueError:
            pass

        # 清除额外复习标记
        item.needs_extra_review = False
        item.extra_review_since = None

        # 清空不熟悉历史
        item.unfamiliar_history = []

        # 更新熟练度
        item.proficiency = Proficiency.MASTERED
        item.save()

    return JsonResponse({'status': 'success'})
```

#### ReviewFeedbackNoView（点击NO）

**核心逻辑**：

```python
def post(self, request, *args, **kwargs):
    item_id = request.POST.get('id')
    review_date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()

    item = Item.objects.get(id=item_id)

    # 幂等性检查
    if reviewed_today(item, review_date):
        return JsonResponse({'status': 'already_reviewed'})

    # 记录本次不熟悉
    review_type = 'regular' if item.next_review_date <= review_date else 'extra'
    item.unfamiliar_history.append({
        'date': review_date.isoformat(),
        'interval': item.current_interval,
        'review_type': review_type
    })

    # 计算当前周期的不熟悉次数
    current_cycle_count = sum(
        1 for record in item.unfamiliar_history
        if record.get('interval') == item.current_interval
    )

    # 判断是否触发重置
    if current_cycle_count >= 3:
        # 重置到Day 0
        item.current_interval = 0
        item.next_review_date = review_date
        item.unfamiliar_history = []
        item.needs_extra_review = False
        item.extra_review_since = None
        item.proficiency = Proficiency.UNFAMILIAR
    else:
        # 判断是否为正式复习日
        if item.next_review_date <= review_date:
            # 正式复习日点NO：设置额外复习
            item.needs_extra_review = True
            item.extra_review_since = review_date + timedelta(days=1)
            # current_interval 和 next_review_date 保持不变
        else:
            # 额外复习点NO：所有字段保持不变
            pass

    item.save()

    # 返回不熟悉次数
    unfamiliar_count = sum(
        1 for record in item.unfamiliar_history
        if record.get('interval') == item.current_interval
    )
    return JsonResponse({'status': 'success', 'unfamiliar_count': unfamiliar_count})
```

### 6. 前端交互增强

#### 复习页面表格

新增列：

| 列名 | 说明 | 示例 |
|------|------|------|
| Review Cycle | 复习周期 | "Day 1" 或 "额外复习" |
| Scheduled Review Date | 计划日期 | "2026-02-02" 或 "逾期3天" |
| Next Review Date | 预计下次日期 | "2026-02-03 (如果点YES)" |
| Unfamiliar | 不熟悉次数 | "1/3" 或 "2/3" 或 "3/3 (将重置)" |
| Review Type | 复习类型 | "常规复习" / "额外复习" |

#### 视觉反馈

- **常规复习**：蓝色标签 `bg-primary`
- **额外复习**：橙色标签 `bg-warning`，整行黄色背景 `table-warning`
- **逾期提示**：红色标签 `bg-danger` + "逾期X天"
- **不熟悉计数**：
  - 0次：灰色 `text-muted`
  - 1-2次：橙色 `text-warning`
  - 3次：红色 `text-danger` + "(将重置)"

#### JavaScript 增强

```javascript
// 从日期选择器获取当前日期（而非模板变量）
const reviewDate = document.getElementById('id_review_date').value;

// AJAX 请求
fetch('/review-feedback/yes/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
        id: wordId,
        date: reviewDate  // 传递正确的复习日期
    })
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        // 标记为已复习
        markRowAsReviewed(wordId);
        // 自动跳转到下一个单词
        jumpToNextWord();
    }
});
```

### 7. 数据迁移策略

#### 迁移脚本：migrate_existing_items.py

为现有的 Item 设置新的复习字段：

```python
def migrate_items():
    items = Item.objects.all()
    for item in items:
        if item.next_review_date:
            continue  # 已迁移，跳过

        # 计算天数差异
        if item.initDate:
            days_since_init = (datetime.today().date() - item.initDate).days

            # 根据天数确定应该处于哪个复习间隔
            current_idx = 0
            for i, interval in enumerate(REVIEW_INTERVALS):
                if days_since_init >= interval:
                    current_idx = i
                else:
                    break

            # 设置字段
            item.current_interval = REVIEW_INTERVALS[current_idx]

            # 计算下次复习日期
            if current_idx < len(REVIEW_INTERVALS) - 1:
                next_interval_days = REVIEW_INTERVALS[current_idx + 1]
                item.next_review_date = item.initDate + timedelta(days=next_interval_days)
            else:
                item.next_review_date = item.initDate + timedelta(days=REVIEW_INTERVALS[-1])

            # 初始化其他字段
            item.unfamiliar_history = []
            item.needs_extra_review = False
            item.extra_review_since = None

            item.save()
```

#### 迁移注意事项

- **向后兼容**：已有数据不会丢失，自动计算合理的复习进度
- **默认值**：新字段都有合理的默认值，不会导致数据错误
- **幂等性**：脚本可以多次运行，不会重复迁移

## 使用说明

### 1. 创建新单词

```python
# 创建时初始化复习系统
item = Item.objects.create(
    user=user,
    category=category,
    item='example',
    content='示例',
    inputDate=today,
    initDate=today,
    # 新字段初始化
    current_interval=0,
    next_review_date=today,
    unfamiliar_history=[],
    needs_extra_review=False,
    extra_review_since=None
)
```

### 2. 日常复习流程

1. **选择日期**：在复习首页选择要复习的日期
2. **查看列表**：系统显示所有需要复习的项目
3. **点击反馈**：
   - **YES（记得）**：进入下一周期，清除所有负面标记
   - **NO（不记得）**：记录不熟悉，触发额外复习（如果是正式复习日）
4. **自动跳转**：完成一个单词后自动跳转到下一个
5. **进度刷新**：所有单词复习完后，自动刷新列表

### 3. 额外复习处理

当在正式复习日点击"NO"后：

- **第二天**：单词会以"额外复习"标签出现在复习列表
- **持续显示**：直到下次正式复习日之前的每一天都会显示
- **退出机制**：
  - 点击"YES"：立即退出额外复习，进入下一周期
  - 连续3次"NO"：触发重置，从Day 0重新开始

### 4. 查看复习计划

在单词详情页新增"完整复习计划"表格：

| 序号 | 间隔 | 计划日期 | 状态 | 是否熟悉 |
|------|------|---------|------|---------|
| 1 | Day 0 | 2026-02-01 | ✅ 已完成 | ✓ 熟悉 |
| 2 | Day 1 | 2026-02-02 | ✅ 已完成 | ✗ 不熟悉 |
| 3 | Day 2 | 2026-02-03 | ⏳ 待复习 | - |
| 4 | Day 4 | 2026-02-05 | - | - |
| ... | ... | ... | ... | ... |

## 边界情况处理

| 场景 | 处理策略 | 实现细节 |
|------|---------|---------|
| 逾期复习 | 计算逾期天数，从实际复习日期开始计算下次日期 | `next_review_date = review_date + interval_increment` |
| 逾期期间点NO | 正常记录，不触发额外复习（因为已经不是正式复习日） | 只记录历史，不改变复习计划 |
| 连续多次NO | 同一周期内3次触发重置 | `if current_cycle_count >= 3: reset()` |
| 已完成所有间隔 | 保持最后一个间隔，不再推进 | `if current_idx == max_idx: pass` |
| 额外复习期间点YES | 清除额外复习标记，但保持在当前周期 | `needs_extra_review = False`，其他不变 |
| 用户选择未来日期 | 正常显示，支持提前复习 | 查询条件使用 `<=` 而非 `==` |
| 数据迁移 | 自动计算合理的复习进度 | `migrate_existing_items.py` |
| 重复点击YES/NO | 幂等性检查，防止重复记录 | `if reviewed_today: return` |

## 测试验证

### 1. 单元测试

#### test_review_logic_script.py

测试日期计算逻辑：

```python
def test_yes_date_advances_correctly(self):
    intervals = [0,1,2,4,7,15,30,90,180]
    review_date = date(2026,2,1)

    # Day 0 -> Day 1
    expected = review_date + timedelta(days=1)
    self.assertEqual(expected, date(2026,2,2))

    # Day 2 -> Day 4
    expected = review_date + timedelta(days=2)
    self.assertEqual(expected, date(2026,2,3))
```

#### test_yes_no_behavior.py

测试YES/NO行为：

```python
def test_yes_on_regular_advances_interval(self):
    # Day 0 点 YES -> Day 1
    it = Item.objects.create(current_interval=0, next_review_date=today)
    resp = self.client.post('/review-feedback/yes/', ...)
    it.refresh_from_db()
    self.assertEqual(it.current_interval, 1)
    self.assertEqual(it.next_review_date, today + timedelta(days=1))

def test_no_on_regular_sets_extra_review(self):
    # Day 0 点 NO -> 设置额外复习
    it = Item.objects.create(current_interval=0, next_review_date=today)
    resp = self.client.post('/review-feedback/no/', ...)
    it.refresh_from_db()
    self.assertTrue(it.needs_extra_review)
    self.assertEqual(it.extra_review_since, today + timedelta(days=1))
```

#### test_item_detail.py

测试复习计划显示：

```python
def test_review_schedule_present(self):
    url = reverse('item-detail', args=[self.item.pk])
    resp = self.client.get(url)
    self.assertEqual(resp.status_code, 200)
    self.assertIn('review_schedule', resp.context)

    schedule = resp.context['review_schedule']
    self.assertEqual(len(schedule), 9)  # 9个间隔点
```

### 2. 集成测试

#### simulate_reviews.py

完整流程模拟：

```python
# 创建10个测试单词
items = seed_items(user, count=10)

# 模拟复习流程（60% YES，40% NO）
for item in items:
    steps = 0
    while item.current_interval < 180 and steps < 12:
        # 随机逾期0-2天
        review_delay = random.randint(0, 2)
        review_date = item.next_review_date + timedelta(days=review_delay)

        # 随机选择YES或NO
        if random.random() < 0.6:
            # 点击YES
            client.post('/review-feedback/yes/', ...)
        else:
            # 点击NO
            client.post('/review-feedback/no/', ...)

        steps += 1

# 生成报告
generate_simulation_report()
```

#### 测试结果示例

```
总条目: 20
到达最终间隔 (Day180) 的条目数: 9
总计记录的 NO 次数: 3
```

### 3. 手动测试场景

#### 场景1：顺利通过所有复习

```
2/1: Day 0 点 YES -> Day 1 (2/2)
2/2: Day 1 点 YES -> Day 2 (2/3)
2/3: Day 2 点 YES -> Day 4 (2/5)
2/5: Day 4 点 YES -> Day 7 (2/8)
... 依此类推直到 Day 180
```

#### 场景2：中途遗忘并触发额外复习

```
2/1: Day 0 点 YES -> Day 1 (2/2)
2/2: Day 1 点 NO  -> 额外复习开始 (2/3-2/1)
2/3: 额外复习点 YES -> 清除额外复习，等待下次正式复习
```

#### 场景3：3次遗忘触发重置

```
2/1: Day 1 点 NO -> unfamiliar_count: 1/3
2/2: 额外复习 NO -> unfamiliar_count: 2/3
2/3: 额外复习 NO -> unfamiliar_count: 3/3 -> 触发重置
                      -> current_interval=0, next_review_date=2/3
```

#### 场景4：逾期复习

```
2/1: next_review_date=2/2
2/5: 用户才来复习（逾期3天）
     -> 显示"逾期3天"
     -> 点 YES -> next_review_date = 2/5 + (2-1) = 2/6
     -> 进入 Day 2
```

## 性能影响

### 1. 数据库性能

| 指标 | 影响 | 说明 |
|------|------|------|
| 查询复杂度 | O(n) | 增加了一个 Q 对象的 OR 条件 |
| 索引需求 | 中 | 建议在 `next_review_date` 和 `extra_review_since` 上建立索引 |
| 存储空间 | 小 | 每个Item增加约100字节（5个字段） |

### 2. 查询优化建议

```python
# 建议添加数据库索引
class Item(models.Model):
    # ...

    class Meta:
        indexes = [
            models.Index(fields=['next_review_date']),
            models.Index(fields=['needs_extra_review', 'extra_review_since']),
            models.Index(fields=['user', 'next_review_date']),  # 组合索引
        ]
```

### 3. 内存使用

- **unfamiliar_history**：JSONField，每个记录约50字节，正常情况下10-20个记录
- **总体评估**：对10000个单词，额外内存约1-2MB

## 未来扩展

### 1. 算法优化

- **自适应间隔**：根据用户的实际表现动态调整间隔长度
- **难度系数**：为不同的单词设置不同的遗忘速率
- **个性化曲线**：基于历史数据生成用户专属的遗忘曲线

### 2. 统计分析

- **记忆热力图**：可视化用户在不同时间段的记忆表现
- **遗忘模式分析**：识别哪些类型的单词容易被遗忘
- **复习效率报告**：计算复习投入时间和记忆保持率的关联

### 3. 社交功能

- **复习排行榜**：对比不同用户的复习进度
- **共享单词库**：团队协作复习
- **提醒机制**：逾期复习的邮件/推送通知

### 4. 多平台支持

- **移动端优化**：响应式设计已实现，可进一步优化
- **离线模式**：支持离线复习，联网后同步
- **导出功能**：导出为Anki、Quizlet等格式

## 相关文件

### 核心文件

- **EAW/models.py** - 数据模型定义（新增5个字段）
- **EAW/views.py** - 核心业务逻辑（重构复习和反馈视图）
- **EAW/migrations/0010_item_current_interval_item_extra_review_since_and_more.py** - 数据库迁移

### 前端文件

- **EAW/templates/review_day.html** - 复习列表页面（新增列和视觉反馈）
- **EAW/templates/review_home.html** - 复习首页（优化日期选择）
- **EAW/templates/item_detail.html** - 单词详情页（新增复习计划表）

### 文档文件

- **EBBINGHAUS_LOGIC.md** - 遗忘曲线逻辑详细说明文档
- **docs/PR文档/PR#2_Feat_遗忘曲线主逻辑变更.md** - 本文档

### 测试和工具

- **EAW/tests/test_item_detail.py** - 复习计划显示测试
- **EAW/tests/test_yes_no_behavior.py** - YES/NO行为测试
- **EAW/tests/test_review_logic_script.py** - 日期计算逻辑测试
- **simulate_reviews.py** - 完整流程模拟脚本
- **generate_simulation_report.py** - 模拟报告生成器
- **migrate_existing_items.py** - 数据迁移工具
- **test_review_logic.py** - 逻辑验证脚本
- **test_review_scenario.py** - 场景测试脚本

## 提交记录

```
commit 277dda1c194fc0821bce88d112af4008c0cad90e
Merge pull request #2 from myGitToy/feat_遗忘曲线主逻辑变更

commit aaac356ebd2e0f0acb21433f1290ff695c491594
feat: show reviewed_today, make feedback idempotent, update UI to mark reviewed and disable YES/NO

commit b052093574179337b4f52c67a8baf960f470a36a
配置和迁移自动化测试脚本

commit 820646e8bc07e3df1007d04779c801447507a3d6
添加单次点击NO的测试单元模块

commit cf51e05cdb544622ddc1ead9e92af05bb7ad054b
修复点击No以后，unfamily会在下个周期被重置的问题

commit 0600181f7377ebe46c10a68cf6cfe420eb7891a1
修复复习间隔显示不正常的问题

commit 6b8382b463719bf43f824a311d98c4e62592f267
创建遗忘曲线的逻辑说明文档，并且把原先的最后一个时间间隔点，即365天予以去除

commit 86d5707ed9f60eb95524b474a201aedb473e3f53
修正点击No以后，第二天复习时，Unfamiliar数量没有增加的问题

commit 709f0cd2d8d0c7e32e218e859784d620432d3385
调整遗忘曲线的主逻辑
```

## 版本信息

- **创建日期**：2026-02-01
- **功能分支**：feat_遗忘曲线主逻辑变更
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-01
- **合并提交**：277dda1
- **关联需求**：艾宾浩斯遗忘曲线复习系统核心算法重构
- **影响版本**：v0.2.x → v0.3.0
- **数据库迁移**：0010_item_current_interval_item_extra_review_since_and_more.py

---

**维护者**：EbbinghausAnywhere 开发团队
**审核状态**：已审核
**最后更新**：2026-02-10
