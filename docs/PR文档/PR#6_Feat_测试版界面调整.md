# 测试版界面优化与功能简化

> **项目地址**：[EbbinghausAnywhere](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #6
> **创建日期**：2026-02-03
> **功能分支**：feat_测试版界面调整
> **目标分支**：main
> **合并日期**：2026-02-03
> **合并提交**：995d3ae

## 功能概述

对项目进行首个公开发行版的界面优化，隐藏部分高级功能入口，简化用户交互流程，提升移动端适配性，为用户提供简洁明了的学习体验。

## 背景说明

### 设计理念

原项目功能丰富但入口较多，对于首次使用的用户可能造成认知负担。在首个公开发行版中，需要：
- **简化导航**：突出核心功能（每日复习、AI词典），隐藏高级管理功能
- **移动优先**：优化手机端体验，支持横向滚动和响应式布局
- **保留扩展性**：隐藏而非删除功能，保留路由和页面代码，便于后续恢复

### 核心调整

1. **功能简化**：隐藏 Input、Search、Manage Profile、Manage Data 入口
2. **服务重组**：将首页服务入口合并为一行，支持横向滚动
3. **导航优化**：将侧边栏从右侧移至左侧，符合主流应用习惯
4. **移动适配**：优化复习页面表格、卡片标题、字体大小
5. **内容增强**：添加开发日志页面，增加透明度
6. **安全加固**：禁用测试版期间的 AI 配置修改，建立默认管理员账户

## 技术实现

### 1. 导航隐藏策略

使用 Django 模板注释 `{% comment %}`...`{% endcomment %}` 隐藏导航项。

**优势**：
- 保留路由和页面代码
- 无需修改 URL 配置
- 恢复时仅需删除注释块

**实现代码**（`EAW/templates/includes/navbar.html`）：

```django
{% comment %}
注：以下导航项在测试版中临时隐藏，保留路由与页面功能不变。
要恢复：删除本注释块。

<li class="nav-item sidebar-nav-item">
    <a class="nav-link js-scroll-trigger" href="{% url 'input-view' %}">Input</a>
</li>
<!-- 其他隐藏项 -->
{% endcomment %}
```

### 2. 首页服务入口横向滚动

**CSS 改进**（`static/css/styles.css`）：

```css
/* 将首页服务项放成一行，较窄屏幕允许横向滚动 */
#services .row {
    display: flex;
    flex-wrap: nowrap; /* 不换行 */
    justify-content: center;
    gap: 1.25rem;
    overflow-x: auto; /* 小屏幕时横向滚动 */
    -webkit-overflow-scrolling: touch;
    padding-bottom: 0.5rem;
}

#services .row .col-6.col-md-3 {
    flex: 0 0 18%; /* 五项在一行显示 */
    max-width: 18%;
}

@media (max-width: 768px) {
    #services .row .col-6.col-md-3 {
        flex: 0 0 60%; /* 小屏时每个卡片更宽 */
        max-width: 60%;
    }
}
```

**服务入口重新排序**（`EAW/templates/home_logged_in.html`）：

1. **Dict**（AI词典）- 新增核心功能
2. **Daily Review**（每日复习）- 主要功能
3. **All Items**（全部条目）- 查看功能
4. **Calendar**（日历视图）- 计划功能
5. **Statistics**（数据统计）- 分析功能

### 3. 移动端响应式优化

#### 复习页面表格优化

**HTML 改进**（`EAW/templates/review_day.html`）：

```html
<div class="card-body p-0">
    {% if page_obj %}
    <!-- Single Table for All Items with responsive wrapper -->
    <div class="table-responsive">
        <table class="table table-bordered table-hover mb-0">
            <!-- 表格内容 -->
        </table>
    </div>
    {% else %}
    <!-- Empty State -->
    {% endif %}
</div>
```

**CSS 移动端适配**：

```css
@media (max-width: 768px) {
    /* 为表格容器添加横向滚动 */
    .card-body > .table-responsive,
    .card-body > table {
        display: block;
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    /* 调整复习页面的表格字体大小 */
    #review-home table,
    #reviewContent table {
        font-size: 0.75rem;
        min-width: 800px; /* 确保表格有最小宽度可以滚动 */
    }

    /* 调整表头和单元格的内边距 */
    #review-home table th,
    #review-home table td,
    #reviewContent table th,
    #reviewContent table td {
        padding: 0.4rem;
        white-space: nowrap;
    }

    /* 调整徽章大小 */
    #review-home .badge,
    #reviewContent .badge {
        font-size: 0.65rem;
        padding: 0.2em 0.4em;
    }

    /* 调整模态框内容 */
    .modal-body {
        font-size: 0.9rem;
    }
}
```

#### 卡片标题优化

```css
/* 手机端进一步减小卡片头部标题，避免占用过多空间 */
@media (max-width: 480px) {
    .card-header h5 {
        font-size: 1rem;
        padding: 0.5rem;
    }
}
```

### 4. 侧边栏位置调整

将侧边栏从右侧移至左侧，符合主流 Web 应用的导航习惯。

**CSS 实现**：

```css
/* 将侧边栏导航从右侧改为左侧 */
#sidebar-wrapper {
    right: auto !important;
    left: 0 !important;
    transform: translateX(-250px) !important;
    border-left: none !important;
    border-right: 1px solid rgba(255,255,255,.1) !important;
}

#sidebar-wrapper.active {
    right: auto !important;
    left: 250px !important;
}

.menu-toggle {
    right: auto !important;
    left: 15px !important;
}
```

### 5. 开发日志页面

**新增路由**（`EAW/urls.py`）：

```python
path('dev-log/', views.dev_log, name='dev_log'),
```

**视图函数**（`EAW/views.py`）：

```python
def dev_log(request):
    """
    渲染仓库根下的 DEVELOPMENT_LOG.md 为 HTML 并显示（与 readme_view 风格一致）。
    """
    devlog_path = os.path.join(settings.BASE_DIR, 'DEVELOPMENT_LOG.md')
    if os.path.exists(devlog_path):
        with open(devlog_path, 'r', encoding='utf-8') as f:
            md = f.read()
        html_content = markdown.markdown(md, extensions=['fenced_code', 'tables'])
    else:
        html_content = '<p>No development log found.</p>'

    return render(request, 'dev_log.html', {'content': html_content})
```

**模板文件**（`EAW/templates/dev_log.html`）：

```django
{% extends "base_generic.html" %}
{% load static %}
{% block content %}
<div class="container my-4">
    <div class="row">
        <div class="col-12">
            <h1>Development Log</h1>
            <hr/>
            <div class="dev-log-content">
                {{ content|safe }}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 6. SEO 优化

为 DeepSeek 相关页面添加 HTML `<title>` 标签，改善搜索引擎优化。

**改进前**：

```django
{% block title %}DeepSeek API 配置{% endblock %}
```

**改进后**：

```django
{% block title %}<title>DeepSeek API 配置</title>{% endblock %}
```

### 7. 测试版安全限制

**禁用 AI 配置修改**（`EAW/templates/deepseek_config.html`）：

```django
<div class="alert alert-warning" role="alert">测试版期间暂时无法进行AI模型的配置修改</div>

<div class="d-grid gap-2">
    <button type="submit" class="btn btn-secondary btn-lg" disabled aria-disabled="true">
        <i class="fa fa-save"></i> 保存配置
    </button>
    <!-- 其他按钮 -->
</div>
```

### 8. 默认管理员账户

**数据库迁移**（`EAW/migrations/0011_set_admin_superuser.py`）：

```python
def set_admin_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    try:
        user_qs = User.objects.filter(username='admin')
        if user_qs.exists():
            user = user_qs.first()
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            # 如果不存在，则创建一个不可登录的超级用户（需随后设置密码）
            user = User.objects.create(
                username='admin',
                email='g.huiqiao@gmail.com',
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            try:
                user.set_unusable_password()
                user.save()
            except Exception:
                # 某些 Django 版本下通过 apps.get_model 返回的 User 可能不含 set_unusable_password
                pass
    except Exception:
        # 在迁移中尽量不要中断整个迁移流程
        return
```

**依赖关系**：

```python
dependencies = [
    ('EAW', '0010_item_current_interval_item_extra_review_since_and_more'),
]
```

### 9. DeepSeek 温度参数说明优化

**模型字段更新**（`EAW/models.py`）：

```python
temperature = models.FloatField(
    default=1.0,
    help_text="生成温度 (0.0-2.0)，数据抽取、英语词典建议1.0，翻译建议1.3，创意写作建议1.5"
)
```

**变更说明**：在 help_text 中明确"英语词典"使用温度 1.0，提升用户理解。

## 使用说明

### 用户界面变化

#### 首页服务入口

测试版中仅显示以下 5 个核心服务：

1. **Dict**（AI词典）- 使用 DeepSeek 查询单词
2. **Daily Review**（每日复习）- 核心学习功能
3. **All Items**（全部条目）- 查看所有学习内容
4. **Calendar**（日历视图）- 查看复习计划
5. **Statistics**（数据统计）- 学习数据分析

#### 导航菜单

**显示的导航项**：
- Review（复习）
- Dict（词典）
- All Items（全部条目）
- Calendar（日历）
- Read Me（使用说明）
- Dev Log（开发日志）
- Contact（联系）
- Log out（登出）

**隐藏的导航项**（保留路由）：
- Input（录入）
- Search（搜索）
- Manage Profile（管理个人资料）
- Manage Data（管理数据）

### 恢复隐藏功能

**方法**：编辑 `EAW/templates/includes/navbar.html`，删除 `{% comment %}`...`{% endcomment %}` 块。

**示例**：

```django
<!-- 删除以下注释块 -->
{% comment %}
<li class="nav-item sidebar-nav-item">
    <a class="nav-link js-scroll-trigger" href="{% url 'input-view' %}">Input</a>
</li>
{% endcomment %}
```

恢复后：

```django
<li class="nav-item sidebar-nav-item">
    <a class="nav-link js-scroll-trigger" href="{% url 'input-view' %}">Input</a>
</li>
```

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| 用户访问隐藏功能 URL | 页面仍然可用，仅导航入口被隐藏 |
| 移动端表格内容过长 | 添加横向滚动，最小宽度 800px |
| 侧边栏在小屏幕显示 | 点击汉堡菜单按钮从左侧滑出 |
| 开发日志文件不存在 | 显示 "No development log found." 提示 |
| admin 用户已存在 | 仅更新权限为 staff 和 superuser |
| admin 用户不存在 | 创建新用户并设置不可用密码，需后续修改 |

## 测试验证

### 手动测试清单

#### 桌面端（≥768px）

- [ ] 首页服务项在一行显示，无横向滚动
- [ ] 侧边栏从左侧滑出
- [ ] 导航菜单不显示 Input、Search、Manage Profile、Manage Data
- [ ] 直接访问隐藏功能 URL（如 `/input/`）仍然可用
- [ ] 开发日志页面正常渲染 Markdown 内容

#### 移动端（<768px）

- [ ] 首页服务项支持横向滚动
- [ ] 复习页面表格支持横向滚动
- [ ] 表格字体大小为 0.75rem，内边距为 0.4rem
- [ ] 卡片标题字体为 1rem，内边距为 0.5rem
- [ ] 徽章字体为 0.65rem，内边距为 0.2em 0.4em
- [ ] 模态框字体为 0.9rem

#### 功能测试

- [ ] DeepSeek 配置页面显示警告且保存按钮禁用
- [ ] admin 用户被设置为超级用户（检查数据库）
- [ ] DeepSeek 页面标题包含 `<title>` 标签

### 性能测试

- [ ] CSS 横向滚动不影响页面加载性能
- [ ] Markdown 渲染性能可接受（开发日志 100+ 行）
- [ ] 移动端响应式切换流畅

## 性能影响

- **CSS 增加**：约 +100 行（响应式样式）
- **HTML 修改**：约 12 个文件，主要是模板注释和结构调整
- **Python 代码**：+15 行（dev_log 视图）
- **数据库迁移**：+48 行（admin 用户设置）
- **文档新增**：+106 行（DEVELOPMENT_LOG.md）

**总体评估**：变更主要集中在前端表现层，对后端性能影响极小。

## 未来扩展

### 功能恢复计划

1. **Input 功能**：优化表单后恢复入口
2. **Search 功能**：增加高级搜索后恢复入口
3. **Manage Profile**：简化界面后恢复入口
4. **Manage Data**：添加权限控制后恢复入口

### 界面优化方向

1. **暗色模式**：支持明暗主题切换
2. **多语言**：支持英文界面
3. **个性化设置**：允许用户自定义导航项显示
4. **快捷键**：添加键盘快捷键支持
5. **拖拽排序**：允许用户自定义服务项顺序

### 移动端增强

1. **PWA 支持**：添加离线功能和桌面图标
2. **手势操作**：支持左右滑动切换页面
3. **语音输入**：集成语音识别录入单词
4. **本地通知**：复习提醒推送

## 相关文件

### 前端模板

- `EAW/templates/home_logged_in.html` - 首页服务入口
- `EAW/templates/includes/navbar.html` - 导航栏
- `EAW/templates/review_day.html` - 复习页面
- `EAW/templates/deepseek_config.html` - AI配置页面
- `EAW/templates/deepseek_query.html` - AI查询页面
- `EAW/templates/dev_log.html` - 开发日志页面

### 样式文件

- `static/css/styles.css` - 响应式样式

### Python 代码

- `EAW/urls.py` - URL 路由
- `EAW/views.py` - 视图函数
- `EAW/models.py` - DeepSeek 温度参数说明
- `EAW/migrations/0011_set_admin_superuser.py` - 数据库迁移

### 文档

- `DEVELOPMENT_LOG.md` - 开发日志

## 提交记录

```
commit 995d3ae
Merge pull request #6 from myGitToy/feat_测试版界面调整

commit 8e86f17
更新开发日志

commit 6a29c60
创建迁移任务，建立默认的超级管理员admin账户

commit 1c05e6f
修订deepseek温度设置中的说明文字

commit 17b54c5
feat: disable DeepSeek config saving during beta; add warning in template

commit dfe404e
优化手机端卡片头部标题样式，减小字体和内边距以改善阅读体验

commit 94796dc
调整 DeepSeek 页面标题块，添加 HTML 标题标签以改善 SEO

commit ab46274
更新开发日志，添加最近的提交记录

commit 1511dc0
调整侧边栏导航位置，将其从右侧改为左侧，并优化相关样式

commit e9d84ef
调整复习页面表格的响应式处理，添加横向滚动支持并优化字体和内边距，适配手机页面

commit 559f16a
调整测试版界面，合并服务项为一行并支持横向滚动，统一入口界面的各项元素

commit 89e6240
调整测试版界面，隐藏部分功能入口，保留路由与页面，未来可以迅速恢复

commit 65bf8ad
调整测试版导航项的注释格式，用于隐藏部分导航项

commit beef76f
更新开发日志

commit d85899b
更新开发日志

commit 49cdd8e
创建并更新开发日志

commit 37ed96e
添加首页显示开发日志的功能

commit 0e465d1
测试版：隐藏导航入口（Input、Search、Manage Profile、Manage Data）和主页图标入口（Input、Search）；保留路由与页面功能，便于恢复。
```

## 版本信息

- **创建日期**：2026-02-03
- **功能分支**：feat_测试版界面调整
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-03
- **合并提交**：995d3ae
- **关联需求**：首个公开发行版界面优化
- **变更文件数**：12
- **总增加行数**：+334
- **总删除行数**：-38
- **总变更行数**：372

---

**维护者**：myGitToy
**审核状态**：已审核
**最后更新**：2026-02-10
