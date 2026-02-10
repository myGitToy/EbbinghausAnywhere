# 用户积分系统

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #9
> **创建日期**：2026-02-07
> **功能分支**：feat_积分系统
> **目标分支**：main
> **合并日期**：2026-02-07
> **合并提交**：90d0eb4

## 功能概述

为 EbbinghausAnywhere 记忆系统添加完整的积分系统，包括每日签到、积分获取、积分商城等功能，通过游戏化机制提升用户粘性和学习积极性。

## 背景说明

在语言学习应用中，用户保持持续学习的动力是最大的挑战之一。通过引入积分系统，可以实现：

- **激励机制**：通过签到奖励和学习任务奖励，激励用户每日使用
- **成就反馈**：积分积累给用户带来成就感
- **功能扩展**：为未来的付费功能和特权打下基础
- **数据分析**：通过积分记录分析用户行为

本 PR 实现了完整的积分系统框架，包括签到、商城、兑换等核心功能。

## 技术实现

### 1. 数据模型设计

#### UserPoints 模型

用户积分账户，记录当前积分和等级信息：

```python
class UserPoints(models.Model):
    user = OneToOneField(User, on_delete=models.CASCADE)
    points = IntegerField(default=0)  # 当前积分
    level = IntegerField(default=1)    # 用户等级
    consecutive_days = IntegerField(default=0)  # 连续签到天数
    last_check_in = DateField(null=True)  # 最后签到日期
```

**字段说明**：
- `points`：用户当前积分余额
- `level`：用户等级（预留扩展）
- `consecutive_days`：连续签到天数，用于计算递增奖励
- `last_check_in`：最后签到日期，用于判断是否连续

#### PointRecord 模型

积分流水记录，记录所有积分变动：

```python
class PointRecord(models.Model):
    user = ForeignKey(User, on_delete=models.CASCADE)
    points_change = IntegerField()  # 积分变动（正为增加，负为减少）
    reason = CharField(max_length=100)  # 变动原因
    created_at = DateTimeField(auto_now_add=True)
```

**积分来源**：
- `daily_login`：每日登录奖励（默认 5 积分）
- `daily_check_in`：签到奖励（5-15 积分，随连续天数递增）
- `task_completion`：完成任务奖励
- `redemption`：兑换商品扣除

#### MallItem 模型

积分商城商品：

```python
class MallItem(models.Model):
    name = CharField(max_length=100)
    description = TextField()
    points_cost = IntegerField()  # 所需积分
    stock = IntegerField(default=0)  # 库存（-1 表示无限）
    is_active = BooleanField(default=True)
```

#### RedemptionRecord 模型

兑换记录：

```python
class RedemptionRecord(models.Model):
    user = ForeignKey(User, on_delete=models.CASCADE)
    item = ForeignKey(MallItem, on_delete=models.CASCADE)
    points_cost = IntegerField()
    redeemed_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=20)  # pending/completed/cancelled
```

### 2. 签到功能实现

#### 签到奖励算法

连续签到奖励递增机制：

```python
def calculate_check_in_reward(consecutive_days):
    """
    根据连续签到天数计算奖励
    - 1-3天：5积分
    - 4-7天：10积分
    - 8天及以上：15积分
    """
    if consecutive_days < 3:
        return 5
    elif consecutive_days < 7:
        return 10
    else:
        return 15
```

#### 签到逻辑

```python
def daily_check_in(user):
    user_points, created = UserPoints.objects.get_or_create(user=user)
    today = timezone.now().date()

    # 检查是否已签到
    if user_points.last_check_in == today:
        return {'success': False, 'message': '今日已签到'}

    # 判断是否连续
    yesterday = today - timedelta(days=1)
    if user_points.last_check_in == yesterday:
        user_points.consecutive_days += 1
    else:
        user_points.consecutive_days = 1

    # 计算奖励
    reward = calculate_check_in_reward(user_points.consecutive_days)
    user_points.points += reward
    user_points.last_check_in = today
    user_points.save()

    # 记录流水
    PointRecord.objects.create(
        user=user,
        points_change=reward,
        reason=f'签到奖励（连续{user_points.consecutive_days}天）'
    )

    return {'success': True, 'reward': reward, 'consecutive_days': user_points.consecutive_days}
```

### 3. 积分商城功能

#### 商品展示

```python
def get_mall_items():
    return MallItem.objects.filter(is_active=True, stock__gte=0)
```

#### 兑换逻辑

```python
def redeem_item(user, item_id):
    user_points = UserPoints.objects.get(user=user)
    item = MallItem.objects.get(id=item_id)

    # 检查积分是否足够
    if user_points.points < item.points_cost:
        return {'success': False, 'message': '积分不足'}

    # 检查库存
    if item.stock == 0:
        return {'success': False, 'message': '商品已售罄'}

    # 扣除积分
    user_points.points -= item.points_cost
    user_points.save()

    # 更新库存
    if item.stock > 0:
        item.stock -= 1
    item.save()

    # 创建兑换记录
    RedemptionRecord.objects.create(
        user=user,
        item=item,
        points_cost=item.points_cost,
        status='pending'
    )

    # 记录流水
    PointRecord.objects.create(
        user=user,
        points_change=-item.points_cost,
        reason=f'兑换商品：{item.name}'
    )

    return {'success': True}
```

### 4. 自动登录奖励

在用户登录时自动发放每日登录奖励：

```python
def user_login_signal(sender, user, **kwargs):
    today = timezone.now().date()

    # 检查今日是否已领取登录奖励
    existing = PointRecord.objects.filter(
        user=user,
        reason='每日登录奖励',
        created_at__date=today
    ).exists()

    if not existing:
        user_points, _ = UserPoints.objects.get_or_create(user=user)
        user_points.points += 5
        user_points.save()

        PointRecord.objects.create(
            user=user,
            points_change=5,
            reason='每日登录奖励'
        )
```

## 使用说明

### 用户签到

1. **访问签到页面**：点击首页"签到"卡片
2. **查看签到状态**：
   - 今日未签到：显示"立即签到"按钮
   - 今日已签到：显示签到日期和奖励
3. **点击签到**：
   - 获得积分奖励
   - 连续签到天数增加
   - 查看明日可获得的积分

### 积分商城

1. **浏览商品**：点击首页"积分商城"卡片
2. **查看商品详情**：点击商品卡片查看详情
3. **兑换商品**：
   - 确认积分足够
   - 点击"立即兑换"
   - 确认兑换操作
4. **查看兑换记录**：在"我的兑换"页面查看历史兑换

### 积分记录

用户可在个人中心查看：
- 当前积分余额
- 签到天数
- 积分流水记录（收入/支出明细）
- 兑换历史

## 积分规则

### 获取积分

| 方式 | 积分 | 限制 |
|------|------|------|
| 每日登录 | +5 | 每天1次 |
| 签到（1-3天） | +5 | 每天1次 |
| 签到（4-7天） | +10 | 每天1次 |
| 签到（8天+） | +15 | 每天1次 |
| 完成学习任务 | +10~50 | 根据任务难度 |

### 积分消耗

- 兑换虚拟商品：消耗相应积分
- 兑换学习资料：消耗相应积分
- 积分解锁高级功能：（预留）

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| 连续签到中断 | 重置为1天，从第一天开始重新计算 |
| 跨时区登录 | 使用服务器时间（UTC）判断日期 |
| 库存不足 | 显示"已售罄"，禁用兑换按钮 |
| 并发签到 | 使用数据库事务确保只签到一次 |
| 积分不足兑换 | 前端禁用按钮，后端再次校验 |

## 性能影响

- **数据库查询**：每次登录增加1次查询（检查今日是否已领奖）
- **索引优化**：在 `created_at` 字段建立索引，快速查询今日记录
- **缓存策略**：用户积分信息缓存5分钟，减少数据库查询

## 测试验证

### 单元测试

1. **签到测试**
   - 测试首次签到获得5积分
   - 测试连续签到奖励递增
   - 测试中断后重置
   - 测试重复签到被拒绝

2. **兑换测试**
   - 测试积分不足时兑换失败
   - 测试库存扣减
   - 测试并发兑换

3. **登录奖励测试**
   - 测试每日首次登录获得奖励
   - 测试同日多次登录只获得一次奖励

### 手动验证步骤

1. 创建测试用户
2. 执行连续签到7天
3. 验证积分计算正确：
   - 第1-3天：5积分/天
   - 第4-7天：10积分/天
4. 中断一天，验证重置为5积分
5. 兑换测试商品，验证积分扣除和库存更新

## 数据库迁移

```python
# 生成迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate

# 创建测试数据
python manage.py shell
>>> from EAW.models import MallItem
>>> MallItem.objects.create(name='测试商品', points_cost=100, stock=10)
```

## 未来扩展

1. **等级系统**：根据积分设置用户等级，解锁不同特权
2. **任务系统**：添加每日任务、每周任务、成就任务
3. **排行榜**：积分排名、连续签到排名
4. **积分抽奖**：消耗积分参与抽奖
5. **社交功能**：积分赠送、积分PK
6. **付费功能**：支持购买积分

## 相关文件

- `EAW/models.py` - 数据模型定义
- `EAW/views.py` - 视图函数
- `EAW/templates/mall.html` - 积分商城页面
- `EAW/templates/check_in.html` - 签到页面
- `EAW/tests/test_points_system.py` - 积分系统测试

## 提交记录

```
commit 90d0eb4
Merged PR #9: Feat 积分系统

commit 9ae37f3
修正连续签到错误的问题

commit a3936f7
增加积分系统的测试文档

commit 27ba048
增加积分商城和兑换功能

commit e72f6b5
增加和调整md文档位置
```

## 版本信息

- **创建日期**：2026-02-07
- **功能分支**：feat_积分系统
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-07
- **合并提交**：90d0eb4
- **关联需求**：用户激励机制

---

**维护者**：myGitToy
**审核状态**：已审核
**最后更新**：2026-02-10
