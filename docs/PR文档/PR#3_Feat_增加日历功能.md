# 新增复习日历功能

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #3
> **创建日期**：2026-02-01
> **功能分支**：feat_增加日历功能
> **目标分支**：main
> **合并日期**：2026-02-01
> **合并提交**：e97a9e8

## 功能概述

在艾宾浩斯记忆学习系统中新增日历功能，以月视图展示每日学习计划和单词复习安排，帮助用户直观查看历史复习记录和未来学习计划。

## 背景说明

在艾宾浩斯遗忘曲线学习法中，定期复习是记忆保持的关键：
- **周期性复习**：按照特定间隔（0、1、2、4、7、15、30、90、180天）进行复习
- **学习可视化**：用户需要直观看到每天的复习计划和完成情况
- **历史回顾**：查看过去的学习记录和复习状态
- **计划前瞻**：了解未来几天的学习安排

现有系统只提供今日复习功能，无法从时间维度整体规划学习。本功能通过集成 FullCalendar 日历库，将复习计划以日历形式呈现，支持月视图和周视图切换。

## 技术实现

### 1. FullCalendar 集成

#### 前端库引入

使用本地化的 FullCalendar v6 Global Bundle，包含完整功能和内联样式：

```html
<!-- EAW/templates/calendar_month.html -->
<script src="{% static 'fullcalendar/fullcalendar.min.js' %}"></script>
```

**选择原因**：
- Global Bundle 包含所有插件和内联样式，无需额外加载 CSS
- 支持中文本地化（locale: 'zh-cn'）
- 事件驱动架构，便于动态加载复习数据
- 成熟稳定，API 完善且文档丰富

#### 日历初始化配置

```javascript
// static/js/calendar.js
calendarInstance = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'zh-cn',
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,dayGridWeek'
    },
    buttonText: {
        today: '今天',
        month: '月',
        week: '周'
    },
    // ... 事件处理配置
});
```

**核心特性**：
- 月视图和周视图切换
- 中文界面和日期格式
- 自定义工具栏按钮
- 事件点击和日期点击交互
- 悬浮提示框

### 2. 数据获取与展示

#### 后端 API 设计

**1. 日历事件 API：`/api/calendar-events/`**

返回指定时间范围内按天聚合的复习统计。

**请求参数**：
- `start`: 开始日期（ISO 8601 格式）
- `end`: 结束日期（ISO 8601 格式）

**响应格式**（FullCalendar Event Object）：
```json
[
    {
        "id": "2026-02-01",
        "title": "今日: 5待 · 3已完成",
        "start": "2026-02-01",
        "allDay": true,
        "backgroundColor": "#ffc107",
        "borderColor": "#ffc107",
        "extendedProps": {
            "today_planned": 8,
            "today_pending": 5,
            "today_completed": 3,
            "extra": 2
        }
    }
]
```

**核心逻辑**（`EAW/views.py` 第 665-787 行）：

```python
@login_required
def calendar_events_api(request):
    """返回指定时间范围内按天聚合的复习统计，FullCalendar 兼容格式。"""
    start_date = parse_date_safe(start, datetime.today().date() - timedelta(days=30))
    end_date = parse_date_safe(end, datetime.today().date() + timedelta(days=30))

    for i in range(days + 1):
        d = start_date + timedelta(days=i)

        # 1. 今日计划：next_review_date 正好是今天
        today_planned = Item.objects.filter(
            user=request.user,
            next_review_date=d
        )

        # 2. 额外复习：需要额外复习且在复习期内
        extra_review = Item.objects.filter(
            user=request.user
        ).filter(
            Q(needs_extra_review=True, extra_review_since__lte=d, next_review_date__gt=d) |
            Q(next_review_date__isnull=True, needs_extra_review=True, extra_review_since__lte=d)
        )

        # 统计完成情况（通过 unfamiliar_history 判断）
        # ... 统计逻辑

        # 构建事件对象
        events.append({
            'id': d.isoformat(),
            'title': title,
            'start': d.isoformat(),
            'allDay': True,
            'backgroundColor': color,
            'extendedProps': { ... }
        })
```

**2. 日期详情 API：`/api/calendar-day-items/`**

返回指定日期的复习条目列表，用于详情弹窗显示。

**请求参数**：
- `date`: 日期字符串（ISO 8601 格式）

**响应格式**：
```json
{
    "items": [
        {
            "id": 123,
            "item": "apple",
            "interval_day": 7,
            "next_review_date": "2026-02-01",
            "reviewed_today": false,
            "unfamiliar_count": 2,
            "is_extra_review": false,
            "detail_url": "/item/123/"
        }
    ]
}
```

**核心逻辑**（`EAW/views.py` 第 791-880 行）：

```python
@login_required
def calendar_day_items_api(request):
    """返回指定日期的复习条目列表（JSON）。"""
    d = datetime.fromisoformat(date_str).date()

    # 查询今日计划和额外复习
    review_items = Item.objects.filter(user=request.user).filter(
        Q(next_review_date=d) |
        Q(needs_extra_review=True, extra_review_since__lte=d, next_review_date__gt=d) |
        Q(next_review_date__isnull=True, needs_extra_review=True, extra_review_since__lte=d)
    ).order_by('next_review_date', 'item')

    # 构建响应数据
    for it in review_items:
        # 判断是否今日已点评
        reviewed_today = any(r.get('date') == d.isoformat() for r in uh)

        # 统计不熟悉次数
        unfamiliar_count = sum(...)

        items.append({
            'id': it.id,
            'item': it.item,
            'interval_day': cur_day,
            'next_review_date': it.next_review_date,
            'reviewed_today': reviewed_today,
            'unfamiliar_count': unfamiliar_count,
            'is_extra_review': is_extra,
            'detail_url': reverse('item-detail', kwargs={'pk': it.id})
        })
```

### 3. 前端展示与交互

#### 日历事件渲染

**自定义事件内容**（`static/js/calendar.js` 第 77-101 行）：

```javascript
eventContent: function(arg) {
    const event = arg.event;
    const props = event.extendedProps;

    let html = '<div class="fc-event-main-frame">';
    html += '<div class="fc-event-title-container">';
    html += `<div class="fc-event-title fc-sticky">${arg.event.title}</div>`;

    // 显示详细分类信息
    let details = [];
    if (todayPending > 0) details.push(`今日待: ${todayPending}`);
    if (todayCompleted > 0) details.push(`已完成: ${todayCompleted}`);
    if (extra > 0) details.push(`额外: ${extra}`);

    if (details.length > 0) {
        html += `<div class="fc-event-subtitle">${details.join(' | ')}</div>`;
    }

    return { html: html };
}
```

**颜色编码系统**：
- 绿色（#28a745）：全部完成，无待办
- 黄色（#ffc107）：有今日待办
- 蓝色（#007bff）：其他情况（仅额外复习）

#### 日期详情弹窗

**触发方式**：
1. 点击日历日期格子（`dateClick`）
2. 点击事件标题（`eventClick`）

**弹窗内容**（`static/js/calendar.js` 第 359-452 行）：

```javascript
function openDayModal(dateStr) {
    // 显示模态框
    $('#calendarDayModal').modal('show');

    // 获取当天复习项目
    fetch(`/api/calendar-day-items/?date=${dateStr}`)
        .then(resp => resp.json())
        .then(data => {
            renderDayItems(data.items, dateStr, modalBody);
        });
}

function renderDayItems(items, dateStr, container) {
    // 按类别分组
    const todayPlanned = [];  // 今日计划
    const extra = [];          // 额外复习

    // 渲染今日计划区块
    if (todayPlanned.length > 0) {
        mainDiv.appendChild(createCategorySection('今日计划', todayPlanned, dateStr, 'primary'));
    }

    // 渲染额外复习区块
    if (extra.length > 0) {
        mainDiv.appendChild(createCategorySection('额外复习', extra, dateStr, 'warning'));
    }
}
```

**每个复习项显示**：
- 单词内容
- 复习周期（间隔天数）
- 不熟悉次数徽章
- 已点评状态
- 下次复习日期
- 操作按钮组（详情、已掌握、不熟、重置）

#### 悬浮提示框

**触发时机**：鼠标悬停在事件上（延迟 300ms 显示）

**功能**（`static/js/calendar.js` 第 170-319 行）：
- 动态创建悬浮窗元素
- 调用日期详情 API 获取数据
- 智能定位（避免超出视口）
- 显示单词列表预览（今日计划最多 10 个，额外复习最多 5 个）
- 点击提示框可打开完整详情弹窗

#### 反馈操作集成

**直接在弹窗中完成复习反馈**（`static/js/calendar.js` 第 526-586 行）：

```javascript
function handleFeedback(action, itemId, dateStr, itemDiv) {
    const urlMap = {
        'yes': '/review-feedback/yes/',
        'no': '/review-feedback/no/',
        'reset': '/review-feedback/reset/'
    };

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ id: parseInt(itemId), date: dateStr })
    })
    .then(resp => resp.json())
    .then(resp => {
        if (resp && resp.success) {
            // 更新UI显示已点评
            btnGroup.innerHTML = '<span class="badge badge-success">已点评</span>';
            // 刷新日历事件
            calendarInstance.refetchEvents();
        }
    });
}
```

### 4. 路由配置

**URL 映射**（`EAW/urls.py` 第 199-201 行）：

```python
# Calendar page and APIs
path('calendar/', views.calendar_month_view, name='calendar-month'),
path('api/calendar-events/', views.calendar_events_api, name='calendar-events-api'),
path('api/calendar-day-items/', views.calendar_day_items_api, name='calendar-day-items-api'),
```

### 5. 样式设计

**日历容器样式**（`static/css/calendar.css`）：

```css
#calendar {
  max-width: 1200px;
  margin: 20px auto;
  padding: 0 15px;
  min-height: 600px;
  opacity: 1 !important;
  visibility: visible !important;
}

.fc-event {
  cursor: pointer;
  border-radius: 3px;
  padding: 2px 4px;
}

.fc-day-today {
  background-color: #fff3cd !important;  /* 高亮今天 */
}

/* 悬浮窗样式 */
.calendar-tooltip {
  position: absolute;
  background: white;
  border: 1px solid #ddd;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  border-radius: 4px;
  padding: 10px;
  max-width: 300px;
  z-index: 10000;
}
```

**响应式设计**（`@media (max-width: 768px)`）：
- 调整工具栏布局为垂直堆叠
- 减小内边距
- 优化模态框宽度

## 使用说明

### 访问日历

1. **登录后主页入口**：
   - 主页新增 "Calendar" 图标入口
   - 点击日历图标进入月视图

2. **未登录用户**：
   - 主页显示 "查看日历（需要登录）" 链接
   - 点击后跳转至登录页面

### 日历视图操作

1. **切换月份**：
   - 点击工具栏 "上一月/下一月" 按钮
   - 点击 "今天" 快速返回当前月份
   - 点击标题选择特定月份和年份

2. **切换视图**：
   - 点击 "月" 按钮切换到月视图
   - 点击 "周" 按钮切换到周视图

3. **查看日期详情**：
   - 点击任意日期格子查看当天复习计划
   - 点击事件标题快速查看详情
   - 鼠标悬停查看简要预览

4. **完成复习**：
   - 在详情弹窗中直接点击 "已掌握" 或 "不熟" 按钮
   - 提交后自动刷新日历显示
   - 点击 "详情" 查看完整单词信息

### 信息解读

**事件标题含义**：
- "今日: 5待 · 3已完成"：今日计划 8 个单词，已完成 3 个，待复习 5 个
- "额外: 2"：额外复习 2 个单词
- "无待办"：当天无复习计划

**颜色编码**：
- 🟢 绿色：全部完成
- 🟡 黄色：有待办
- 🔵 蓝色：仅额外复习

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| 日期参数缺失 | 使用默认值：前 30 天到后 30 天 |
| 日期格式错误 | 尝试多种解析方式，失败则返回默认日期 |
| 无复习计划的日期 | 不显示事件（日历格子为空） |
| API 请求失败 | 显示错误提示，日历保持当前状态 |
| FullCalendar 加载失败 | 显示友好的错误提示和刷新按钮 |
| CSRF Token 缺失 | 从 cookie 中自动提取 |
| 大量数据渲染 | 悬浮窗和弹窗限制显示数量（10/5） |
| 网络请求超时 | 显示加载状态，失败后提示重试 |

## 已知问题说明

### 切换月份时学习计划刷不出

**问题描述**：
在日历视图中切换到其他月份时，学习计划无法正常显示。

**原因分析**：
1. FullCalendar 的 `datesSet` 回调已正确配置
2. 后端 API 已记录日志显示接收到请求
3. 可能的原因：
   - 事件加载函数 `events` 回调未正确触发
   - API 返回的数据格式不匹配
   - 日历实例状态未正确更新

**临时解决方案**：
1. 刷新页面重新加载日历
2. 点击 "今天" 按钮回到当前月份
3. 清除浏览器缓存后重试

**待修复**：
需要进一步调试 `datesSet` 回调和事件加载逻辑，确保月份切换时正确触发 API 请求并渲染数据。

### 其他限制

1. **不支持拖拽**：无法通过拖拽调整复习日期
2. **不支持批量操作**：只能逐个完成复习反馈
3. **移动端体验**：在小屏幕上悬浮窗定位可能不准确

## 测试验证

### 功能测试用例

1. **日历渲染测试**
   - 验证 FullCalendar 正确加载和渲染
   - 检查月视图和周视图切换
   - 测试今天日期高亮显示

2. **数据加载测试**
   - 初始加载时显示当月数据
   - 切换月份时触发 API 请求
   - 验证事件标题和颜色正确显示

3. **交互测试**
   - 点击日期打开详情弹窗
   - 点击事件标题打开详情弹窗
   - 鼠标悬停显示悬浮提示
   - 弹窗中完成复习反馈
   - 验证反馈后日历自动刷新

4. **边界测试**
   - 无复习计划的日期不显示事件
   - 空数据时显示提示信息
   - API 错误时显示友好提示
   - 大量数据时性能测试

5. **兼容性测试**
   - Chrome、Firefox、Safari、Edge
   - 桌面端和移动端
   - 不同屏幕尺寸

### 手动验证步骤

1. 准备测试数据：创建多个不同复习日期的单词
2. 访问日历页面，验证初始加载
3. 切换月份，验证数据更新（注意已知问题）
4. 点击日期查看详情弹窗
5. 在弹窗中完成复习反馈
6. 验证日历事件自动刷新
7. 测试悬浮提示功能
8. 验证响应式布局

## 性能影响

- **初始加载**：增加 FullCalendar 库（~400KB）
- **API 请求**：
  - 月视图初始加载：1 次请求（获取当月数据）
  - 切换月份：1 次请求
  - 打开详情弹窗：1 次请求
- **数据库查询**：每次请求查询指定日期范围的复习数据
- **内存占用**：日历实例缓存事件数据，约几十 KB
- **渲染性能**：每月最多 31 个事件，渲染流畅

**优化建议**：
- 实现服务端分页，避免一次性加载过多数据
- 添加本地缓存（localStorage）减少重复请求
- 使用虚拟滚动优化大量数据渲染

## 未来扩展

1. **多视图支持**：
   - 日视图（显示当天的详细时间线）
   - 列表视图（类似任务列表）
   - 时间线视图（横向展示复习进度）

2. **交互增强**：
   - 拖拽调整复习日期
   - 批量复习反馈
   - 快捷键支持（键盘导航）

3. **统计分析**：
   - 月度复习完成率统计
   - 连续复习天数记录
   - 学习热力图
   - 导出复习报告

4. **个性化设置**：
   - 自定义颜色方案
   - 调整事件显示密度
   - 设置复习提醒

5. **移动端优化**：
   - 原生 App 集成
   - 离线数据支持
   - 推送通知

6. **修复已知问题**：
   - 解决切换月份数据加载问题
   - 优化悬浮窗定位算法
   - 改进错误处理机制

## 相关文件

### 后端文件

- `EAW/views.py` - 日历视图和 API 实现（第 654-880 行）
- `EAW/urls.py` - 路由配置（第 199-201 行）

### 前端模板

- `EAW/templates/calendar_month.html` - 日历页面主模板
- `EAW/templates/home_logged_in.html` - 主页日历入口（修改）
- `EAW/templates/home_logged_out.html` - 未登录主页提示（修改）
- `EAW/templates/base_generic.html` - Favicon 图标（修改）

### 静态资源

- `static/js/calendar.js` - 日历前端逻辑（621 行）
- `static/css/calendar.css` - 日历样式（275 行）
- `static/fullcalendar/fullcalendar.min.js` - FullCalendar 库（本地化）
- `static/test-fullcalendar.html` - FullCalendar 加载测试页面
- `static/calendar-debug.html` - 调试测试页面

### 其他文件

- `static/templates/includes/scripts.html` - MathJax 渲染兼容性修改（第 20-37 行）

## 提交记录

```
commit e97a9e83acfc76bcda668d0c1ba74a8de3a8a560
Author: myGitToy
Date: 2026-02-01
    增加日历视图中显示全部单词复习计划的功能

commit 174b36a775b91bc56e34759f136bcf2fb3d9d956
Author: myGitToy
Date: 2026-02-01
    修正日历渲染的问题
```

## 版本信息

- **创建日期**：2026-02-01
- **功能分支**：feat_增加日历功能
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-01
- **合并提交**：e97a9e8
- **关联需求**：艾宾浩斯学习系统功能增强

---

**维护者**：Claude Code
**审核状态**：已审核
**最后更新**：2026-02-10
