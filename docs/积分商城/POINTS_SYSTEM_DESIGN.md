# 积分系统设计文档

## 一、系统概述

### 1.1 功能目标
- 用户每完成一个单词复习可获得1积分
- 积分可在商城兑换游戏时长（1积分=1分钟）
- 记录所有积分变动历史

### 1.2 涉及模块
- 数据模型（models.py）
- 视图逻辑（views.py）
- URL路由（urls.py）
- 前端模板（templates）
- 管理后台（admin.py）

---

## 二、数据库设计

### 2.1 UserPoints（用户积分账户）

```python
class UserPoints(models.Model):
    """用户积分账户"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='points_account',
        verbose_name='用户'
    )
    current_points = models.IntegerField(
        default=0,
        verbose_name='当前积分',
        help_text='用户当前可用积分'
    )
    total_earned = models.IntegerField(
        default=0,
        verbose_name='累计获得',
        help_text='用户累计获得的总积分'
    )
    total_spent = models.IntegerField(
        default=0,
        verbose_name='累计消费',
        help_text='用户累计消费的总积分'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '用户积分账户'
        verbose_name_plural = '用户积分账户'
    
    def __str__(self):
        return f'{self.user.username} - {self.current_points}积分'
    
    def add_points(self, amount, reason, source_type='review'):
        """增加积分"""
        self.current_points += amount
        self.total_earned += amount
        self.save()
        
        # 创建交易记录
        PointsTransaction.objects.create(
            user=self.user,
            transaction_type='earn',
            amount=amount,
            balance_after=self.current_points,
            reason=reason,
            source_type=source_type
        )
        return True
    
    def deduct_points(self, amount, reason, redemption_type='game_time'):
        """扣除积分"""
        if self.current_points < amount:
            return False  # 积分不足
        
        self.current_points -= amount
        self.total_spent += amount
        self.save()
        
        # 创建交易记录
        PointsTransaction.objects.create(
            user=self.user,
            transaction_type='spend',
            amount=amount,
            balance_after=self.current_points,
            reason=reason,
            redemption_type=redemption_type
        )
        return True
```

### 2.2 PointsTransaction（积分交易记录）

```python
class PointsTransaction(models.Model):
    """积分交易记录"""
    TRANSACTION_TYPES = (
        ('earn', '获得积分'),
        ('spend', '消费积分'),
    )
    
    SOURCE_TYPES = (
        ('review', '复习单词'),
        ('bonus', '系统奖励'),
        ('admin', '管理员调整'),
    )
    
    REDEMPTION_TYPES = (
        ('game_time', '游戏时长'),
        ('other', '其他'),
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='points_transactions',
        verbose_name='用户'
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        verbose_name='交易类型'
    )
    amount = models.IntegerField(
        verbose_name='积分数量'
    )
    balance_after = models.IntegerField(
        verbose_name='交易后余额'
    )
    reason = models.CharField(
        max_length=200,
        verbose_name='原因说明'
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        null=True,
        blank=True,
        verbose_name='获得来源'
    )
    redemption_type = models.CharField(
        max_length=20,
        choices=REDEMPTION_TYPES,
        null=True,
        blank=True,
        verbose_name='兑换类型'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='交易时间'
    )
    
    class Meta:
        verbose_name = '积分交易记录'
        verbose_name_plural = '积分交易记录'
        ordering = ['-created_at']
    
    def __str__(self):
        type_display = self.get_transaction_type_display()
        return f'{self.user.username} - {type_display} {self.amount}积分'
```

### 2.3 RewardItem（奖励商品）

```python
class RewardItem(models.Model):
    """奖励商品"""
    name = models.CharField(
        max_length=100,
        verbose_name='商品名称'
    )
    description = models.TextField(
        verbose_name='商品描述'
    )
    points_cost = models.IntegerField(
        verbose_name='所需积分',
        help_text='兑换该商品需要的积分数'
    )
    item_type = models.CharField(
        max_length=50,
        default='game_time',
        verbose_name='商品类型',
        help_text='如: game_time, physical_reward等'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='排序'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        verbose_name = '奖励商品'
        verbose_name_plural = '奖励商品'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f'{self.name} ({self.points_cost}积分)'
```

---

## 三、URL路由设计

在 `urls.py` 中添加：

```python
urlpatterns = [
    # ... 现有路由 ...
    
    # 积分系统路由
    path('points/', views.points_home, name='points-home'),
    path('points/shop/', views.points_shop, name='points-shop'),
    path('points/redeem/', views.redeem_points, name='redeem-points'),
    path('points/history/', views.points_history, name='points-history'),
]
```

---

## 四、视图函数设计

### 4.1 积分首页

```python
@login_required
def points_home(request):
    """积分系统首页"""
    # 获取或创建用户积分账户
    points_account, created = UserPoints.objects.get_or_create(user=request.user)
    
    # 获取最近的交易记录
    recent_transactions = PointsTransaction.objects.filter(
        user=request.user
    )[:10]
    
    # 统计数据
    stats = {
        'current_points': points_account.current_points,
        'total_earned': points_account.total_earned,
        'total_spent': points_account.total_spent,
        'transaction_count': PointsTransaction.objects.filter(user=request.user).count(),
    }
    
    context = {
        'points_account': points_account,
        'recent_transactions': recent_transactions,
        'stats': stats,
    }
    
    return render(request, 'points_home.html', context)
```

### 4.2 积分商城

```python
@login_required
def points_shop(request):
    """积分商城"""
    points_account, created = UserPoints.objects.get_or_create(user=request.user)
    
    # 获取可用商品列表
    reward_items = RewardItem.objects.filter(is_active=True)
    
    context = {
        'points_account': points_account,
        'reward_items': reward_items,
    }
    
    return render(request, 'points_shop.html', context)
```

### 4.3 兑换积分

```python
@login_required
def redeem_points(request):
    """兑换积分处理"""
    if request.method != 'POST':
        return redirect('points-shop')
    
    points_account, created = UserPoints.objects.get_or_create(user=request.user)
    
    # 获取兑换参数
    minutes = int(request.POST.get('minutes', 0))
    
    if minutes <= 0:
        messages.error(request, '请输入有效的兑换时长')
        return redirect('points-shop')
    
    # 检查积分是否足够（1积分=1分钟）
    required_points = minutes
    if points_account.current_points < required_points:
        messages.error(request, f'积分不足！需要{required_points}积分，当前仅有{points_account.current_points}积分')
        return redirect('points-shop')
    
    # 扣除积分
    success = points_account.deduct_points(
        amount=required_points,
        reason=f'兑换游戏时长 {minutes} 分钟',
        redemption_type='game_time'
    )
    
    if success:
        messages.success(request, f'成功兑换 {minutes} 分钟游戏时长！已扣除 {required_points} 积分')
    else:
        messages.error(request, '兑换失败，请稍后再试')
    
    return redirect('points-shop')
```

### 4.4 积分历史

```python
@login_required
def points_history(request):
    """积分历史记录"""
    # 获取筛选参数
    transaction_type = request.GET.get('type', 'all')
    
    # 基础查询
    transactions = PointsTransaction.objects.filter(user=request.user)
    
    # 应用筛选
    if transaction_type != 'all':
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # 分页
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 获取账户信息
    points_account, created = UserPoints.objects.get_or_create(user=request.user)
    
    context = {
        'points_account': points_account,
        'page_obj': page_obj,
        'transaction_type': transaction_type,
    }
    
    return render(request, 'points_history.html', context)
```

### 4.5 修改复习视图（添加积分奖励）

在现有的 `review_view` 函数中，当用户点击"YES"时添加积分：

```python
# 在复习成功的逻辑处添加：
if request.method == 'POST' and 'yes' in request.POST:
    # ... 原有的复习逻辑 ...
    
    # 添加积分奖励
    points_account, created = UserPoints.objects.get_or_create(user=request.user)
    points_account.add_points(
        amount=1,
        reason=f'复习单词: {item.item}',
        source_type='review'
    )
```

---

## 五、模板设计

### 5.1 积分首页（points_home.html）

```html
{% extends "base_generic.html" %}

{% block content %}
<div class="container mt-4">
    <h2>我的积分</h2>
    
    <!-- 积分卡片 -->
    <div class="row mt-4">
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">当前积分</h5>
                    <h2 class="text-primary">{{ stats.current_points }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">累计获得</h5>
                    <h2 class="text-success">{{ stats.total_earned }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">累计消费</h5>
                    <h2 class="text-warning">{{ stats.total_spent }}</h2>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 快捷入口 -->
    <div class="row mt-4">
        <div class="col-md-6">
            <a href="{% url 'points-shop' %}" class="btn btn-primary btn-lg btn-block">
                🛒 积分商城
            </a>
        </div>
        <div class="col-md-6">
            <a href="{% url 'points-history' %}" class="btn btn-secondary btn-lg btn-block">
                📊 积分历史
            </a>
        </div>
    </div>
    
    <!-- 最近交易 -->
    <div class="mt-5">
        <h4>最近交易</h4>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>类型</th>
                    <th>积分</th>
                    <th>说明</th>
                    <th>余额</th>
                </tr>
            </thead>
            <tbody>
                {% for trans in recent_transactions %}
                <tr>
                    <td>{{ trans.created_at|date:"Y-m-d H:i" }}</td>
                    <td>
                        {% if trans.transaction_type == 'earn' %}
                        <span class="badge badge-success">获得</span>
                        {% else %}
                        <span class="badge badge-warning">消费</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if trans.transaction_type == 'earn' %}
                        <span class="text-success">+{{ trans.amount }}</span>
                        {% else %}
                        <span class="text-danger">-{{ trans.amount }}</span>
                        {% endif %}
                    </td>
                    <td>{{ trans.reason }}</td>
                    <td>{{ trans.balance_after }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

### 5.2 积分商城（points_shop.html）

```html
{% extends "base_generic.html" %}

{% block content %}
<div class="container mt-4">
    <h2>积分商城</h2>
    
    <!-- 当前积分显示 -->
    <div class="alert alert-info">
        <strong>当前积分：</strong> {{ points_account.current_points }} 分
    </div>
    
    <!-- 游戏时长兑换 -->
    <div class="card mt-4">
        <div class="card-header bg-primary text-white">
            <h4>🎮 游戏时长兑换</h4>
        </div>
        <div class="card-body">
            <p class="card-text">1 积分 = 1 分钟游戏时长</p>
            
            <form method="post" action="{% url 'redeem-points' %}">
                {% csrf_token %}
                <div class="form-group">
                    <label for="minutes">兑换时长（分钟）：</label>
                    <input type="number" 
                           class="form-control" 
                           id="minutes" 
                           name="minutes" 
                           min="1" 
                           max="{{ points_account.current_points }}"
                           placeholder="请输入要兑换的分钟数"
                           required>
                </div>
                <button type="submit" class="btn btn-success">立即兑换</button>
            </form>
        </div>
    </div>
    
    <!-- 其他商品（预留扩展） -->
    {% if reward_items %}
    <div class="mt-5">
        <h4>更多奖励</h4>
        <div class="row">
            {% for item in reward_items %}
            <div class="col-md-4 mb-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">{{ item.name }}</h5>
                        <p class="card-text">{{ item.description }}</p>
                        <p class="text-primary"><strong>{{ item.points_cost }} 积分</strong></p>
                        <button class="btn btn-primary" disabled>敬请期待</button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
```

### 5.3 积分历史（points_history.html）

```html
{% extends "base_generic.html" %}

{% block content %}
<div class="container mt-4">
    <h2>积分历史</h2>
    
    <!-- 筛选器 -->
    <div class="btn-group mt-3" role="group">
        <a href="?type=all" class="btn btn-outline-primary {% if transaction_type == 'all' %}active{% endif %}">全部</a>
        <a href="?type=earn" class="btn btn-outline-success {% if transaction_type == 'earn' %}active{% endif %}">获得</a>
        <a href="?type=spend" class="btn btn-outline-warning {% if transaction_type == 'spend' %}active{% endif %}">消费</a>
    </div>
    
    <!-- 交易记录表 -->
    <div class="table-responsive mt-4">
        <table class="table table-hover">
            <thead class="thead-light">
                <tr>
                    <th>交易时间</th>
                    <th>类型</th>
                    <th>积分变动</th>
                    <th>说明</th>
                    <th>交易后余额</th>
                </tr>
            </thead>
            <tbody>
                {% for trans in page_obj %}
                <tr>
                    <td>{{ trans.created_at|date:"Y-m-d H:i:s" }}</td>
                    <td>
                        {% if trans.transaction_type == 'earn' %}
                        <span class="badge badge-success">{{ trans.get_transaction_type_display }}</span>
                        {% else %}
                        <span class="badge badge-warning">{{ trans.get_transaction_type_display }}</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if trans.transaction_type == 'earn' %}
                        <span class="text-success font-weight-bold">+{{ trans.amount }}</span>
                        {% else %}
                        <span class="text-danger font-weight-bold">-{{ trans.amount }}</span>
                        {% endif %}
                    </td>
                    <td>{{ trans.reason }}</td>
                    <td class="font-weight-bold">{{ trans.balance_after }}</td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="5" class="text-center">暂无交易记录</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- 分页 -->
    {% if page_obj.has_other_pages %}
    <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
            {% if page_obj.has_previous %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.previous_page_number }}&type={{ transaction_type }}">上一页</a>
            </li>
            {% endif %}
            
            <li class="page-item disabled">
                <span class="page-link">第 {{ page_obj.number }} / {{ page_obj.paginator.num_pages }} 页</span>
            </li>
            
            {% if page_obj.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.next_page_number }}&type={{ transaction_type }}">下一页</a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
</div>
{% endblock %}
```

---

## 六、管理后台配置

在 `admin.py` 中添加：

```python
from .models import UserPoints, PointsTransaction, RewardItem

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_points', 'total_earned', 'total_spent', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'balance_after', 'reason', 'created_at')
    list_filter = ('transaction_type', 'source_type', 'redemption_type', 'created_at')
    search_fields = ('user__username', 'reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

@admin.register(RewardItem)
class RewardItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_cost', 'item_type', 'is_active', 'sort_order')
    list_filter = ('is_active', 'item_type')
    search_fields = ('name', 'description')
```

---

## 七、数据库迁移步骤

```bash
# 1. 创建迁移文件
python manage.py makemigrations

# 2. 查看SQL语句（可选）
python manage.py sqlmigrate EAW xxxx

# 3. 执行迁移
python manage.py migrate

# 4. 创建游戏时长商品（可选，通过Django shell）
python manage.py shell
>>> from EAW.models import RewardItem
>>> RewardItem.objects.create(
...     name='游戏时长',
...     description='每1积分可兑换1分钟游戏时间',
...     points_cost=1,
...     item_type='game_time',
...     is_active=True
... )
```

---

## 八、测试计划

### 8.1 功能测试
- [ ] 用户复习单词后是否正确获得1积分
- [ ] 积分账户显示是否正确
- [ ] 积分商城兑换功能是否正常
- [ ] 积分不足时是否正确提示
- [ ] 积分历史记录是否准确
- [ ] 筛选和分页是否正常工作

### 8.2 边界测试
- [ ] 兑换0分钟或负数时的处理
- [ ] 积分余额为0时的兑换
- [ ] 超过余额的兑换请求

### 8.3 并发测试
- [ ] 多个复习请求同时到达时积分计算是否准确
- [ ] 同时兑换时积分扣除是否正确

---

## 九、扩展功能建议

### 9.1 短期扩展
1. **每日签到奖励**：连续签到额外奖励
2. **成就系统**：完成特定目标获得额外积分
3. **排行榜**：展示积分排名激励学习

### 9.2 长期扩展
1. **实物奖励**：书籍、文具等实体商品
2. **积分转赠**：用户之间可以转赠积分
3. **积分有效期**：设置积分过期机制
4. **多倍积分活动**：特定时间段获得双倍积分

---

## 十、注意事项

1. **数据一致性**：使用事务确保积分增减的原子性
2. **安全性**：积分兑换需要CSRF保护和用户验证
3. **性能优化**：考虑对历史记录进行索引优化
4. **用户体验**：积分变动及时反馈给用户
5. **监控日志**：记录所有积分变动便于审计

---

## 十一、实施时间线

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| 第1天 | 创建数据模型和迁移 | 2小时 |
| 第2天 | 实现视图函数 | 3小时 |
| 第3天 | 创建前端模板 | 3小时 |
| 第4天 | 集成到复习流程 | 2小时 |
| 第5天 | 测试和修复bug | 2小时 |

**总计：约12小时**

---

## 十二、相关文件清单

需要修改/创建的文件：
- ✅ `EAW/models.py` - 添加3个新模型
- ✅ `EAW/views.py` - 添加4个视图函数，修改1个现有视图
- ✅ `EAW/urls.py` - 添加4条URL路由
- ✅ `EAW/admin.py` - 添加3个管理类
- ✅ `EAW/templates/points_home.html` - 新建
- ✅ `EAW/templates/points_shop.html` - 新建
- ✅ `EAW/templates/points_history.html` - 新建
- ✅ `EAW/templates/base_generic.html` - 添加积分系统导航链接

---

**文档版本**：v1.0  
**创建日期**：2026-02-05  
**最后更新**：2026-02-05
