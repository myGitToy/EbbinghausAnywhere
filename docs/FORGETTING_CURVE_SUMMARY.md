# 遗忘曲线逻辑总结

## 项目概述

**EbbinghausAnywhere** 是一个基于 Django 的开源 Web 应用，实现了艾宾浩斯遗忘曲线的记忆强化系统，专门为用户 Ellie 设计用于英语词汇学习。

### 技术栈
- **后端**: Django 4.1 + Python 3.11
- **前端**: Bootstrap 5
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **部署**: Docker + Nginx
- **AI 集成**: DeepSeek API
- **TTS**: 文本转语音支持

---

## 遗忘曲线逻辑详解

### 核心复习间隔

系统使用固定的 9 个复习间隔点：

```python
intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
```

| 间隔天数 | 复习次数 |
|---------|---------|
| Day 0   | 第1次复习（创建当天） |
| Day 1   | 第2次复习 |
| Day 2   | 第3次复习 |
| Day 4   | 第4次复习 |
| Day 7   | 第5次复习 |
| Day 15  | 第6次复习 |
| Day 30  | 第7次复习 |
| Day 90  | 第8次复习 |
| Day 180 | 第9次复习 |

### 关键数据模型字段

在 `EAW/models.py:87-110` 中定义：

```python
class Item(models.Model):
    next_review_date = models.DateField(...)      # 下次复习日期
    current_interval = models.IntegerField(...)   # 当前间隔 (0,1,2,4,7,15,30,90,180)
    needs_extra_review = models.BooleanField(...)  # 是否需要额外复习
    extra_review_since = models.DateField(...)     # 额外复习开始日期
    unfamiliar_history = models.JSONField(...)     # 不熟悉历史记录
    proficiency = models.IntegerField(...)        # 掌握程度 (UNFAMILIAR/MASTERED)
```

### 复习逻辑实现位置

**核心逻辑**: `EAW/views.py:814-1073`

#### 1. 点击 YES（记得）

- 进入下一个间隔周期
- 计算新的 `next_review_date = 当前日期 + (下个间隔 - 当前间隔)`
- 清除额外复习标记和不熟悉历史
- 更新 `proficiency = MASTERED`

**计算示例**:
```
当前: Day 2 (interval = 2)
下一个: Day 4 (interval = 4)
距离下次复习: 4 - 2 = 2 天
```

#### 2. 点击 NO（不记得）

- 记录不熟悉事件到 `unfamiliar_history`
- **同一周期内 3 次不熟悉** → 重置到 Day 0，从头开始
- **不足 3 次** → 保持当前周期，触发额外复习

#### 3. 额外复习机制

- **触发条件**: 在正式复习日点 NO 后触发
- **表现**: 黄色背景高亮，显示"额外复习"标签
- **结束条件**: 点 YES 或到达原定复习日

#### 4. 3 次重置机制

```python
if current_cycle_count >= 3:
    current_interval = 0
    next_review_date = 今天
    unfamiliar_history = []
    # 从 Day 0 重新开始
```

### 查询逻辑

**位置**: `EAW/views.py:602-666`

单词显示条件（满足其一）：
```python
Q(next_review_date <= review_date) |  # 正式复习日到了
Q(needs_extra_review=True,
  extra_review_since__lte=review_date,
  next_review_date__gt=review_date)    # 额外复习期间
```

---

## 关键设计原则

1. **日期驱动**: 使用绝对日期 `next_review_date` 而非相对计算，避免重复显示
2. **周期独立**: 每个 interval 的不熟悉次数独立统计
3. **保持周期**: 点 NO 不进入下一周期，直到点 YES
4. **额外复习时限**: 只在下次正式复习日之前有效
5. **3 次重置**: 同一周期 3 次不熟悉触发重置
6. **历史清空**: 进入下一周期时清空不熟悉历史，重新计数

---

## 完整场景示例

### 顺利通过场景
```
2月1日: 创建单词 → current_interval=0, next_review_date=2月1日
2月1日: 点YES    → current_interval=1, next_review_date=2月2日
2月2日: 点YES    → current_interval=2, next_review_date=2月3日
2月3日: 点YES    → current_interval=4, next_review_date=2月5日
2月5日: 点YES    → current_interval=7, next_review_date=2月8日
...依此类推
```

### 点NO触发额外复习场景
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

### 3次不熟悉重置场景
```
2月1日: Day 1点NO  → unfamiliar_count: 1/3, 设置额外复习
2月2日: 额外复习NO → unfamiliar_count: 2/3
2月3日: 额外复习NO → unfamiliar_count: 3/3
        → 触发重置: current_interval=0, next_review_date=2月3日
        → 从Day 0重新开始
```

---

## 相关文件

| 文件 | 说明 |
|-----|------|
| [EAW/models.py](EAW/models.py) | 数据模型定义 |
| [EAW/views.py](EAW/views.py) | 复习逻辑实现 |
| [EBBINGHAUS_LOGIC.md](EBBINGHAUS_LOGIC.md) | 完整逻辑文档 |
| [EAW/tests/test_review_logic.py](EAW/tests/test_review_logic.py) | 日期计算测试 |

---

## 系统特性

- 多用户支持，数据独立
- AI 集成（DeepSeek）获取智能单词释义
- TTS 语音朗读支持
- 日历视图可视化复习计划
- 导入/导出功能
- 支持数学公式（MathJax）和化学方程式（mhchem）
