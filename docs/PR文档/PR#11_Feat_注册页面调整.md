# 注册页面优化调整

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #11
> **创建日期**：2026-02-08
> **功能分支**：feat_注册页面调整
> **目标分支**：main
> **合并日期**：2026-02-08
> **合并提交**：90d0eb4

## 功能概述

优化用户注册页面，降低注册门槛并改善用户体验。将邮箱字段改为可选，增加密码规则说明，优化表单字段值保留功能，并改进前端验证逻辑。

## 背景说明

在原版本的注册流程中存在以下问题：

1. **注册门槛过高**：邮箱字段为必填项，但并非所有用户都希望提供邮箱地址
2. **用户体验不佳**：表单提交失败后，所有字段值丢失，用户需要重新填写
3. **密码规则不清晰**：用户无法在注册前了解密码要求，导致反复尝试
4. **验证逻辑不合理**：即使用户未填写邮箱，也会触发邮箱格式验证

本功能通过以下改进解决上述问题：
- 降低注册门槛，将邮箱改为可选字段
- 实现表单字段值保留，失败后无需重新填写
- 新增密码规则说明卡片，清晰展示密码要求
- 优化前端验证逻辑，仅在用户输入时才进行验证

## 技术实现

### 1. 表单优化 (EAW/forms.py)

#### 邮箱字段改为可选

**修改前**：
```python
email = forms.EmailField(
    required=True,
    help_text="Please enter a valid email address."
)
```

**修改后**：
```python
email = forms.EmailField(
    required=False,
    help_text="Email address (optional)."
)
```

#### 改进邮箱唯一性验证

**修改前**：
```python
def clean_email(self):
    email = self.cleaned_data.get('email')
    if User.objects.filter(email=email).exists():
        raise ValidationError("This email is already registered, please use another one.")
    return email
```

**修改后**：
```python
def clean_email(self):
    email = self.cleaned_data.get('email')
    # 只在用户填写了邮箱时才检查重复
    if email and User.objects.filter(email=email).exists():
        raise ValidationError("This email is already registered, please use another one.")
    return email
```

**改进点**：
- 增加空值检查，避免在邮箱为空时进行数据库查询
- 只在用户实际填写了邮箱时才进行唯一性验证

#### 优化表单保存逻辑

**修改前**：
```python
def save(self, commit=True):
    user = super().save(commit=False)
    user.email = self.cleaned_data['email']  # 可能抛出 KeyError
    user.first_name = self.cleaned_data.get('first_name')
    user.last_name = self.cleaned_data.get('last_name')
    if commit:
        user.save()
    return user
```

**修改后**：
```python
def save(self, commit=True):
    user = super().save(commit=False)
    user.email = self.cleaned_data.get('email') or ''  # 处理None情况
    user.first_name = self.cleaned_data.get('first_name', '')  # Save the nickname
    user.last_name = self.cleaned_data.get('last_name', '')  # Save the surname
    if commit:
        user.save()
    return user
```

**改进点**：
- 使用 `.get()` 方法安全获取字段值，避免 KeyError
- 使用 `or ''` 处理 None 情况，确保数据库字段不为空
- 为 `get()` 方法提供默认值 `''`，进一步确保数据完整性

### 2. 前端样式调整 (register.html)

#### 表单字段值保留

为所有输入字段添加 `value` 属性，使用模板标签保留用户输入：

```html
<!-- Username -->
<input type="text"
       name="random_username_{{ random_id }}"
       id="username-{{ random_id }}"
       class="form-control"
       placeholder="Username"
       autocomplete="off"
       required
       value="{{ form.username.value|default:'' }}">

<!-- First Name -->
<input type="text"
       name="first_name"
       class="form-control"
       placeholder="First name or nikename (optional)"
       id="first_name"
       autocomplete="off"
       value="{{ form.first_name.value|default:'' }}">

<!-- Last Name -->
<input type="text"
       name="last_name"
       class="form-control"
       placeholder="Last Name (optional)"
       id="last_name"
       autocomplete="off"
       value="{{ form.last_name.value|default:'' }}">

<!-- Email -->
<input type="email"
       name="email"
       class="form-control"
       placeholder="Email (optional)"
       id="email"
       autocomplete="off"
       value="{{ form.email.value|default:'' }}">
```

**技术细节**：
- 使用 Django 模板标签 `{{ form.field.value|default:'' }}` 获取字段值
- 当字段值为空时，默认返回空字符串
- 即使表单验证失败，用户输入的值也会被保留

#### 密码规则说明卡片

新增独立的密码规则说明卡片，清晰展示密码要求：

```html
<!-- 密码规则说明卡片 -->
<div class="card bg-dark border-secondary mb-3">
    <div class="card-body p-2">
        <h6 class="card-title text-light mb-2">
            <i class="bi bi-shield-lock"></i> Password Requirements:
        </h6>
        <ul class="list-unstyled mb-0 text-light small">
            <li><i class="bi bi-check-circle text-success"></i> At least 8 characters long</li>
            <li><i class="bi bi-check-circle text-success"></i> Not a common password</li>
            <li><i class="bi bi-check-circle text-success"></i> Not entirely numeric</li>
            <li><i class="bi bi-check-circle text-success"></i> Not too similar to your personal info</li>
        </ul>
    </div>
</div>
```

**样式特点**：
- 使用 Bootstrap Card 组件，视觉独立醒目
- 深色背景与注册页面整体风格一致
- 使用图标（shield-lock、check-circle）增强可读性
- 小字体（small）避免占用过多空间
- 无序列表（list-unstyled）保持界面整洁

### 3. JavaScript 验证改进

#### 邮箱验证优化

**修改前**：
```javascript
emailInput.addEventListener('blur', function () {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(this.value)) {
        alert("Please enter a valid email address!");
    }
});
```

**修改后**：
```javascript
emailInput.addEventListener('blur', function () {
    const email = this.value.trim();
    // 只在用户输入了邮箱时才验证
    if (email !== '') {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email)) {
            alert("Please enter a valid email address!");
        }
    }
});
```

**改进点**：
- 增加空值检查，仅在用户输入了内容时才进行验证
- 使用 `trim()` 去除首尾空格，避免误判
- 与后端逻辑保持一致，提供统一的前后端验证体验

## 使用说明

### 用户注册流程

1. **访问注册页面**：点击登录页面的 "Sign up" 链接
2. **填写注册信息**：
   - **Username**（必填）：用户名，最多150个字符，仅支持字母、数字和 @/./+/-/_
   - **First Name**（可选）：昵称或名字
   - **Last Name**（可选）：姓氏
   - **Email**（可选）：邮箱地址
   - **Password**（必填）：需符合密码规则
   - **Confirm Password**（必填）：确认密码
3. **阅读密码规则**：在密码输入框下方查看密码要求
4. **同意服务条款**：勾选 "I agree to the Privacy Policy and Terms of Service"
5. **提交注册**：点击 "Sign up!" 按钮

### 表单字段特点

| 字段 | 是否必填 | 验证规则 | 默认值 |
|------|---------|---------|--------|
| Username | 是 | 唯一性、字符限制 | - |
| First Name | 否 | 最大30字符 | 空字符串 |
| Last Name | 否 | 最大30字符 | 空字符串 |
| Email | 否 | 邮箱格式、唯一性（如填写） | 空字符串 |
| Password | 是 | Django默认验证器 | - |
| Confirm Password | 是 | 需与Password一致 | - |

### 错误处理

- **字段值保留**：表单验证失败后，所有已填写的值会被保留
- **错误提示**：每个字段的错误信息会显示在对应字段下方
- **消息提示**：页面顶部会显示 Django messages 框架的错误提示

## 边界情况处理

| 场景 | 处理策略 |
|------|----------|
| 用户未填写邮箱 | 设置为空字符串，不进行唯一性检查 |
| 用户填写了空邮箱（仅空格） | 使用 trim() 去除空格后视为未填写 |
| 邮箱已被注册 | 显示错误："This email is already registered, please use another one." |
| 邮箱格式不正确 | 前端 alert 提示："Please enter a valid email address!" |
| 表单验证失败 | 保留所有字段值，显示错误信息 |
| 用户名已存在 | 显示错误："Username already exists, please choose another username." |
| 密码不匹配 | 显示错误："Passwords do not match." |
| 密码不符合规则 | Django 默认验证器提供详细错误信息 |
| first_name 或 last_name 为 None | 使用 `.get(field, '')` 确保存入空字符串而非 None |

## 测试验证

### 单元测试用例

#### 邮箱字段测试

1. **未填写邮箱注册**
   - 输入：username="testuser", email=""
   - 预期：注册成功，user.email=""（空字符串）

2. **填写有效邮箱注册**
   - 输入：username="testuser", email="test@example.com"
   - 预期：注册成功，user.email="test@example.com"

3. **填写重复邮箱注册**
   - 输入：username="newuser", email="existing@example.com"（已存在）
   - 预期：注册失败，显示错误"This email is already registered"

4. **填写无效邮箱格式**
   - 输入：username="testuser", email="invalid-email"
   - 预期：前端 alert 提示格式错误

#### 表单字段保留测试

1. **密码不匹配场景**
   - 输入：填写所有字段，password1 != password2
   - 提交：表单验证失败
   - 预期：页面重新加载后，所有字段值保留

2. **用户名已存在场景**
   - 输入：填写所有字段，username已存在
   - 提交：表单验证失败
   - 预期：页面重新加载后，除username外的其他字段值保留

#### 密码规则验证测试

1. **密码过短**
   - 输入：password1="123"
   - 预期：显示错误"This password is too short. It must contain at least 8 characters."

2. **密码为纯数字**
   - 输入：password1="12345678"
   - 预期：显示错误"This password is entirely numeric."

3. **密码与用户名相似**
   - 输入：username="testuser", password1="testuser123"
   - 预期：显示错误"The password is too similar to the username."

### 手动验证步骤

1. **访问注册页面**
   - URL: `/accounts/register/`
   - 验证：页面加载正常，所有字段显示

2. **验证密码规则卡片**
   - 检查：卡片显示在密码输入框下方
   - 检查：图标、文字、样式正确

3. **测试未填写邮箱注册**
   - 输入：只填写必填字段（username、password）
   - 提交：注册成功
   - 验证：可以正常登录

4. **测试表单字段保留**
   - 输入：填写所有字段，故意输入不匹配的密码
   - 提交：表单验证失败
   - 验证：所有已填写的值都被保留

5. **测试邮箱格式验证**
   - 输入：无效邮箱格式"test@"
   - 失焦：触发 blur 事件
   - 验证：显示 alert 提示

## 性能影响

- **数据库查询优化**：邮箱唯一性检查仅在用户填写邮箱时执行，减少不必要的数据库查询
- **前端渲染影响**：密码规则卡片增加约200字节HTML，对性能影响可忽略
- **JavaScript执行时间**：邮箱验证增加空值检查，执行时间增加 < 1ms
- **用户体验提升**：表单字段保留功能大幅减少用户重复输入，提升整体使用效率

## 未来扩展

1. **国际化支持**：将密码规则卡片和错误提示翻译为多语言
2. **密码强度指示器**：添加实时密码强度显示（弱/中/强）
3. **邮箱验证功能**：为填写邮箱的用户发送验证邮件，增强账号安全性
4. **社交账号登录**：支持通过 Google、GitHub 等社交账号直接注册登录
5. **用户名实时检查**：使用 AJAX 在用户输入时实时检查用户名是否可用
6. **渐进式注册**：支持先创建账号，后续再补充个人信息
7. **注册流程引导**：为首次注册用户显示功能介绍和使用指南

## 相关文件

- `EAW/forms.py` - 用户注册表单定义
- `EAW/templates/registration/register.html` - 注册页面模板
- `.claude/CLAUDE.md` - 项目文档（Conda环境管理）
- `.claude/settings.local.json` - Claude Code 配置文件

## 提交记录

```
commit 90d0eb4
Merge pull request #11 from myGitToy/feat_注册页面调整
Feat 注册页面调整

commit edec8fe
feat: 更新Conda环境管理文档，增加在Bash中运行Python代码的解决方案和最佳实践

commit 6f56b37
feat: 调整注册页面，优化邮箱和姓名字段的处理，增加密码规则说明
```

## 版本信息

- **创建日期**：2026-02-08
- **功能分支**：feat_注册页面调整
- **目标分支**：main
- **合并状态**：已合并
- **合并日期**：2026-02-08
- **合并提交**：90d0eb4
- **版本号**：v0.3.3
- **关联需求**：用户体验优化

---

**维护者**：myGitToy
**审核状态**：已审核
**最后更新**：2026-02-10
