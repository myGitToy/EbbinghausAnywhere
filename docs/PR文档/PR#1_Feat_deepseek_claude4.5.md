# DeepSeek API 集成到单词记忆系统

> **项目地址**：[EbbinghausAnywhere - GitHub](https://github.com/myGitToy/EbbinghausAnywhere)
> **PR编号**：PR #1
> **创建日期**：2026-02-01
> **功能分支**：feat_deepseek_claude4.5
> **目标分支**：main
> **合并日期**：2026-02-01
> **合并提交**：c122ad3

## 功能概述

成功集成 DeepSeek AI API 到 EbbinghausAnywhere 单词记忆系统，为用户提供智能单词查询、释义获取和个性化学习体验。该功能与现有的百度翻译 API 完美兼容，用户可以根据需求自由切换使用。

### 核心功能

1. **AI 智能查询** - 使用 DeepSeek AI 获取单词释义、音标和自然例句
2. **个性化配置** - 支持自定义模型、温度参数和系统提示词
3. **一键保存** - 查询结果可直接保存到单词本
4. **TTS 音频播放** - 集成 Google TTS，点击播放单词发音
5. **完美兼容** - 与现有百度翻译 API 共存，保留原有功能
6. **CRUD 增强** - 为单词卡片增加完整的增删改查功能

## 背景说明

在单词学习过程中，高质量的释义和自然例句对记忆效果至关重要。现有的百度翻译 API 虽然提供了基础功能，但存在以下限制：

- **固定输出**：无法调整释义的详细程度和风格
- **例句质量**：机器生成例句不够自然
- **个性化不足**：无法针对不同水平用户调整输出
- **功能单一**：缺少用户自定义配置能力

DeepSeek API 的引入解决了这些问题：

1. **AI 驱动**：利用大语言模型生成更自然的例句和准确的释义
2. **可配置性**：通过温度参数控制生成创造性，通过提示词定制输出格式
3. **用户级配置**：每个用户可以拥有独立的 AI 配置
4. **无缝集成**：完全兼容现有数据结构，无需修改数据库迁移

## 技术实现

### 1. 系统架构

```
┌─────────────┐
│   前端 UI   │
├─────────────┤
│  视图层     │  views.py (Django Views)
├─────────────┤
│  业务层     │  deepseek.py + utils.py
├─────────────┤
│  模型层     │  models.py (DeepSeekConfig)
├─────────────┤
│  API 层     │  OpenAI SDK → DeepSeek API
└─────────────┘
```

### 2. 数据库模型

#### DeepSeekConfig 模型

新增用户级配置表，存储每个用户的 DeepSeek API 配置：

```python
class DeepSeekConfig(models.Model):
    """DeepSeek API 配置模型，每个用户一个配置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    model = models.CharField(max_length=50, default='deepseek-chat')
    temperature = models.FloatField(default=1.0)  # 0.0-2.0
    system_prompt = models.TextField(default='...')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**关键字段说明**：
- `model`：DeepSeek 模型名称，默认 `deepseek-chat`
- `temperature`：生成温度，控制输出的创造性
  - 0.0：代码生成/数学解题（精确）
  - 1.0：数据抽取/分析（推荐用于单词查询）
  - 1.3：通用对话/翻译（灵活）
  - 1.5：创意写作/诗歌（创意）
- `system_prompt`：系统提示词，定义 AI 的行为和输出格式
- `is_active`：启用开关，用户可选择是否使用 DeepSeek

**数据库迁移**：
```python
# EAW/migrations/0009_deepseekconfig.py
migrations.CreateModel(
    name='DeepSeekConfig',
    fields=[
        ('id', models.BigAutoField(...)),
        ('model', models.CharField(...)),
        ('temperature', models.FloatField(default=1.0)),
        ('system_prompt', models.TextField(...)),
        ('is_active', models.BooleanField(default=True)),
        ('user', models.OneToOneField(...)),
    ],
)
```

### 3. 核心 API 调用

#### 模块：`EAW/deepseek.py`

**主要函数**：

##### `call_deepseek_api(word, config=None, user=None)`

调用 DeepSeek API 获取单词释义。

**参数**：
- `word`：要查询的单词
- `config`：DeepSeekConfig 实例（可选）
- `user`：用户实例（可选，用于获取默认配置）

**返回值**：
解析后的 JSON 字典（百度翻译兼容格式），或失败时返回空字典 `{}`

**核心流程**：
```python
# 1. 获取配置（参数 > 用户配置 > 默认值）
model = config.model if config else 'deepseek-chat'
temperature = config.temperature if config else 1.0
system_prompt = config.system_prompt if config else '默认提示词'

# 2. 初始化 OpenAI 客户端（使用 DeepSeek 的 base_url）
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL  # https://api.deepseek.com
)

# 3. 调用 API
response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": word}
    ],
    temperature=temperature,
    stream=False
)

# 4. 解析 JSON 响应（处理 markdown 代码块包裹）
json_data = parse_json_response(response.choices[0].message.content)

# 5. 转换为百度翻译兼容格式
result = parse_deepseek_to_baidu_format(json_data, word)
```

##### `parse_json_response(response_text)`

解析 DeepSeek 返回的 JSON，处理可能的 markdown 代码块包裹。

**处理逻辑**：
```python
# 去除 ```json 或 ``` 标记
if response_text.startswith('```'):
    response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
    response_text = re.sub(r'\n?```\s*$', '', response_text)

# 解析 JSON
json_data = json.loads(response_text.strip())
return json_data
```

**为什么需要这个函数**：
- DeepSeek 有时会在 JSON 前后添加 markdown 代码块标记（\`\`\`json ... \`\`\`）
- 标准的 `json.loads()` 无法解析带有标记的内容
- 此函数确保无论 DeepSeek 返回什么格式，都能正确提取 JSON

##### `parse_deepseek_to_baidu_format(json_data, word)`

将 DeepSeek 返回的 JSON 转换为与百度翻译兼容的格式。

**DeepSeek 格式**：
```json
{
  "uk_phonetic": "/ˈæpl/",
  "us_phonetic": "/ˈæpl/",
  "meaning": "苹果",
  "example_sentences": [
    {"english": "I eat an apple.", "chinese": "我吃一个苹果。"}
  ]
}
```

**百度翻译格式**：
```python
{
  "phonetic": ["英音标", "美音标"],
  "parts_and_means": ["词性: n.\n释义: xxx\n例句1: ..."],
  "simple_meaning": ["简明释义: xxx"],
  "src_tts": "https://translate.google.com/..."
}
```

**转换逻辑**：
```python
# 1. 提取音标
result["phonetic"] = [
  json_data["uk_phonetic"].strip('[]/'),
  json_data["us_phonetic"].strip('[]/')
]

# 2. 提取简明释义
result["simple_meaning"].append(f"简明释义: {json_data['meaning']}")

# 3. 提取例句并格式化
examples_text = []
for idx, example in enumerate(json_data["example_sentences"], 1):
  examples_text.append(f"例句{idx}: {example['english']}")
  examples_text.append(f"翻译: {example['chinese']}")
result["parts_and_means"].append("\n".join(examples_text))

# 4. 生成 Google TTS URL
result["src_tts"] = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}"
```

**设计目的**：
- 保持与百度翻译 API 的数据结构一致性
- 确保前端页面和数据处理逻辑无需修改
- 实现两种翻译服务的无缝切换

### 4. 与百度翻译的兼容性设计

#### 数据流程对比

**百度翻译流程**：
```
用户输入 → baidu_translate() → 返回百度格式 → 保存到数据库
```

**DeepSeek 流程**：
```
用户输入 → deepseek_translate() → call_deepseek_api()
→ 转换为百度格式 → 保存到数据库
```

#### 兼容性实现

在 `utils.py` 中新增 `fetch_and_merge_deepseek()` 函数，与 `fetch_and_merge_translation()` 完全一致的接口：

```python
def fetch_and_merge_deepseek(item_name, existing_content, user=None):
    """
    调用 DeepSeek API 获取释义，返回格式与 fetch_and_merge_translation 完全一致

    :param item_name: 单词名称
    :param existing_content: 现有内容
    :param user: 用户实例（用于获取 DeepSeek 配置）
    :return: (updated_content, src_tts, phonetic_am, phonetic_en)
    """
    translation_result = deepseek_translate(item_name, user=user)

    if not translation_result:
        return existing_content, "", "", ""

    # 解析结果（与百度翻译格式相同）
    parts_and_means = translation_result.get('parts_and_means', [])
    simple_meaning = translation_result.get('simple_meaning', [])
    src_tts = translation_result.get('src_tts', '')
    phonetic = translation_result.get('phonetic', [])

    phonetic_am = phonetic[1] if len(phonetic) > 1 else None
    phonetic_en = phonetic[0] if len(phonetic) > 0 else None

    # 合并新旧内容（使用相同的合并逻辑）
    new_content = "\n".join(parts_and_means if parts_and_means else simple_meaning)
    updated_lines = compare_and_merge(existing_lines, new_lines, threshold=0.8)
    updated_content = "\n".join(updated_lines)

    return updated_content, src_tts, phonetic_am, phonetic_en
```

**兼容性优势**：
- 前端代码无需修改
- 数据库 Item 模型无需新增字段
- 用户可以自由在两种 API 之间切换
- 未来的其他翻译 API 也可以遵循相同模式

### 5. TTS 集成方案

#### Google TTS URL 生成

```python
def generate_tts_url(word):
    """生成 Google TTS 播放链接"""
    return f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}"
```

**前端播放**（在 `item_detail.html` 中）：
```html
<audio id="tts-audio" src="{{ object.src_tts }}"></audio>
<button onclick="document.getElementById('tts-audio').play()">
    <i class="fa fa-volume-up"></i> 播放
</button>
```

**注意事项**：
- Google TTS 可能在中国大陆无法访问
- 用户可以手动替换为其他 TTS 服务（如百度 TTS、讯飞等）
- TTS URL 存储在 Item.src_tts 字段中

### 6. 前端实现

#### DeepSeek 查询页面（`deepseek_query.html`）

**主要元素**：
1. **查询表单**：单词输入框 + 查询按钮
2. **结果展示区**：显示释义、音标、例句
3. **TTS 播放按钮**：点击播放单词发音
4. **保存按钮**：一键保存到单词本
5. **分类选择**：保存时可选择单词分类

**关键交互**：
```javascript
// 1. 查询单词
$('#query-btn').click(function() {
    const word = $('#word-input').val();
    if (!word) return;

    // 禁用按钮，显示加载中
    $('#query-btn').prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> 查询中...');

    // 调用 API
    $.ajax({
        url: '/deepseek/query/',
        method: 'POST',
        data: {
            word: word,
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                displayResult(response.data);
            } else {
                showError(response.error);
            }
        },
        complete: function() {
            $('#query-btn').prop('disabled', false).html('<i class="fa fa-search"></i> 查询');
        }
    });
});

// 2. 显示结果
function displayResult(data) {
    $('#result-word').text(data.word);
    $('#uk-phonetic').text(data.uk_phonetic);
    $('#us-phonetic').text(data.us_phonetic);
    $('#meaning').html(data.meaning.replace(/\n/g, '<br>'));
    $('#examples').html(data.examples);

    // 生成 TTS URL
    const ttsUrl = `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q=${data.word}`;
    $('#tts-audio').attr('src', ttsUrl);

    $('#result-section').removeClass('d-none');
}

// 3. 保存到单词本
$('#save-btn').click(function() {
    const category = $('#category-select').val();

    $.ajax({
        url: '/deepseek/save/',
        method: 'POST',
        data: {
            word: data.word,
            meaning: data.meaning,
            uk_phonetic: data.uk_phonetic,
            us_phonetic: data.us_phonetic,
            src_tts: ttsUrl,
            category: category,
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.success) {
                showSuccess('保存成功！');
            } else {
                showError(response.error);
            }
        }
    });
});
```

#### AI 配置页面（`deepseek_config.html`）

**主要元素**：
1. **模型选择**：下拉选择 DeepSeek 模型（目前仅支持 `deepseek-chat`）
2. **温度设置**：数值输入（0.0-2.0）+ 场景预设（可选）
3. **系统提示词**：多行文本输入
4. **启用开关**：是否启用 DeepSeek API

**温度预设场景**：
```html
<select name="temperature_preset" class="form-control">
    <option value="0.0">代码生成/数学解题 (0.0)</option>
    <option value="1.0" selected>数据抽取/分析 (1.0)</option>
    <option value="1.3">通用对话/翻译 (1.3)</option>
    <option value="1.5">创意写作/诗歌 (1.5)</option>
</select>
```

**自动填充逻辑**：
```javascript
// 选择预设时自动填充温度值
$('select[name="temperature_preset"]').change(function() {
    const value = parseFloat($(this).val());
    $('input[name="temperature"]').val(value);
});
```

#### 单词卡片增强（`item_detail.html`、`item_form.html`）

**新增功能**：
1. **编辑功能**：在单词详情页添加"编辑"按钮
2. **删除功能**：在单词详情页添加"删除"按钮（需二次确认）
3. **DeepSeek 导入**：在编辑页面添加"导入 DeepSeek 释义"按钮

**一键导入实现**：
```javascript
$('#deepseek-import-btn').click(function() {
    const word = $('#id_item').val();
    if (!word) {
        alert('请先输入单词');
        return;
    }

    // 显示加载提示
    $('#loading-alert').removeClass('d-none');
    $(this).prop('disabled', true);

    // 调用 DeepSeek API
    $.ajax({
        url: '/deepseek/query/',
        method: 'POST',
        data: { word: word, csrfmiddlewaretoken: csrf_token },
        success: function(response) {
            if (response.success) {
                // 自动填充表单
                $('#id_content').val(response.data.meaning);
                $('#id_uk_phonetic').val(response.data.uk_phonetic);
                $('#id_us_phonetic').val(response.data.us_phonetic);
                $('#id_src_tts').val(response.data.tts_url);

                // 隐藏加载提示，显示成功消息
                $('#loading-alert').addClass('d-none');
                alert('导入成功！');
            } else {
                alert('导入失败：' + response.error);
            }
        },
        complete: function() {
            $('#deepseek-import-btn').prop('disabled', false);
            $('#loading-alert').addClass('d-none');
        }
    });
});
```

### 7. 后端视图实现

#### 主要视图函数

##### `deepseek_query_view(request)`

处理 DeepSeek 查询请求。

**流程**：
```python
@require_http_methods(["GET", "POST"])
@login_required
def deepseek_query_view(request):
    if request.method == 'POST':
        word = request.POST.get('word', '').strip()
        if not word:
            return JsonResponse({'success': False, 'error': '请输入单词'})

        # 调用 DeepSeek API
        result = call_deepseek_api(word, user=request.user)

        if not result:
            return JsonResponse({'success': False, 'error': '查询失败，请检查 API 配置'})

        # 解析结果
        data = {
            'word': word,
            'uk_phonetic': result.get('phonetic', [''])[0],
            'us_phonetic': result.get('phonetic', [''])[1] if len(result.get('phonetic', [])) > 1 else '',
            'meaning': '\n'.join(result.get('simple_meaning', [])),
            'examples': '\n'.join(result.get('parts_and_means', [])),
            'tts_url': result.get('src_tts', '')
        }

        return JsonResponse({'success': True, 'data': data})

    return render(request, 'deepseek_query.html')
```

##### `deepseek_save_view(request)`

保存 DeepSeek 查询结果到单词本。

**流程**：
```python
@require_http_methods(["POST"])
@login_required
def deepseek_save_view(request):
    word = request.POST.get('word', '').strip()
    meaning = request.POST.get('meaning', '')
    uk_phonetic = request.POST.get('uk_phonetic', '')
    us_phonetic = request.POST.get('us_phonetic', '')
    src_tts = request.POST.get('src_tts', '')
    category_id = request.POST.get('category')

    if not word or not meaning:
        return JsonResponse({'success': False, 'error': '单词和释义不能为空'})

    try:
        # 创建 Item
        item = Item.objects.create(
            user=request.user,
            item=word,
            content=meaning,
            uk_phonetic=uk_phonetic,
            us_phonetic=us_phonetic,
            src_tts=src_tts,
            category_id=category_id,
            inputDate=timezone.now().date(),
            initDate=timezone.now().date()
        )

        return JsonResponse({'success': True, 'message': '保存成功'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
```

##### `deepseek_config_view(request)`

显示和处理 DeepSeek 配置表单。

**流程**：
```python
@login_required
def deepseek_config_view(request):
    # 获取或创建用户配置
    config, created = DeepSeekConfig.objects.get_or_create(
        user=request.user,
        defaults={
            'model': 'deepseek-chat',
            'temperature': 1.0,
            'is_active': True
        }
    )

    if request.method == 'POST':
        form = DeepSeekConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, '配置已保存')
            return redirect('deepseek-config')
    else:
        form = DeepSeekConfigForm(instance=config)

    return render(request, 'deepseek_config.html', {'form': form})
```

##### `check_deepseek_keys_view(request)`

检查 DeepSeek API 密钥是否配置（用于前端显示/隐藏功能入口）。

**流程**：
```python
@require_http_methods(["GET"])
def check_deepseek_keys_view(request):
    """检查是否配置了 DeepSeek API 密钥"""
    is_configured = check_deepseek_keys()
    return JsonResponse({'configured': is_configured})
```

#### 单词 CRUD 视图

##### `ItemUpdateView`

更新单词内容。

```python
@method_decorator(login_required, name='dispatch')
class ItemUpdateView(generic.UpdateView):
    model = Item
    template_name = 'item_form.html'
    fields = ['item', 'content', 'category', 'uk_phonetic', 'us_phonetic', 'src_tts', 'inputDate', 'initDate', 'proficiency']

    def get_queryset(self):
        # 只允许用户编辑自己的 Item
        return Item.objects.filter(user=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 限制 category 只显示当前用户的类别
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        messages.success(self.request, '单词已更新')
        return super().form_valid(form)
```

##### `ItemDeleteView`

删除单词。

```python
@method_decorator(login_required, name='dispatch')
class ItemDeleteView(generic.DeleteView):
    model = Item
    template_name = 'item_confirm_delete.html'
    success_url = reverse_lazy('item-list')

    def get_queryset(self):
        # 只允许用户删除自己的 Item
        return Item.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '单词已删除')
        return super().delete(request, *args, **kwargs)
```

### 8. URL 路由配置

在 `EAW/urls.py` 中新增以下路由：

```python
# DeepSeek API 相关路由
path('deepseek/config/', views.deepseek_config_view, name='deepseek-config'),
path('deepseek/query/', views.deepseek_query_view, name='deepseek-query'),
path('deepseek/save/', views.deepseek_save_view, name='deepseek-save'),
path('api/check-deepseek-keys/', views.check_deepseek_keys_view, name='check-deepseek-keys'),

# 单词 CRUD 路由
path('item/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='item-edit'),
path('item/<int:pk>/delete/', views.ItemDeleteView.as_view(), name='item-delete'),
```

### 9. 环境配置

#### .env 文件配置

```env
# DeepSeek API Configuration
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

#### settings.py 配置

```python
# 读取环境变量
DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default=None)
DEEPSEEK_BASE_URL = env('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')
```

#### 依赖包

在 `requirements.txt` 中新增：

```txt
openai>=1.0.0  # OpenAI SDK（用于调用 DeepSeek API）
```

**注意**：DeepSeek API 兼容 OpenAI SDK，只需修改 `base_url` 即可使用。

## 使用说明

### 1. 初次配置

#### 步骤 1：配置 API 密钥

在项目根目录的 `.env` 文件中添加：

```env
DEEPSEEK_API_KEY=sk-your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

#### 步骤 2：安装依赖

```bash
pip install openai>=1.0.0
```

#### 步骤 3：数据库迁移

```bash
python manage.py migrate
```

这将创建 `EAW_deepseekconfig` 表。

### 2. 功能使用

#### DeepSeek 查询

1. 登录系统
2. 在首页点击"DeepSeek Query"卡片
3. 输入英文单词（如 "apple"）
4. 点击"查询"按钮
5. 查看释义、音标、例句
6. 点击播放按钮试听发音
7. 选择分类并点击"保存到单词本"

#### AI 配置

1. 在首页点击"AI Settings"卡片
2. 配置参数：
   - **模型**：选择 `deepseek-chat`（目前唯一选项）
   - **温度**：输入 0.0-2.0 之间的数值，或选择预设场景
   - **系统提示词**：自定义提示词（推荐使用默认值）
   - **启用开关**：勾选以启用 DeepSeek
3. 点击"保存配置"

#### 单词编辑

1. 在单词详情页点击"编辑"按钮
2. 修改单词内容
3. 点击"导入 DeepSeek"按钮自动填充释义
4. 点击"保存"按钮

#### 单词删除

1. 在单词详情页点击"删除"按钮
2. 确认删除操作
3. 单词将从数据库中移除

### 3. 温度参数选择指南

| 温度值 | 适用场景 | 特点 |
|-------|---------|------|
| 0.0 | 代码生成、数学解题 | 输出精确、确定性高 |
| 1.0 | 数据抽取、英语词典 | 平衡准确性和多样性 ⭐ **推荐** |
| 1.3 | 通用对话、翻译 | 输出更灵活、自然 |
| 1.5 | 创意写作、诗歌 | 创造性强、多样化 |

**单词查询建议**：使用 **1.0**，确保释义准确且例句自然。

## 边界情况处理

### API 调用失败

| 场景 | 处理策略 |
|------|----------|
| API 密钥未配置 | 显示错误提示："请先在 .env 文件中配置 DEEPSEEK_API_KEY" |
| 网络连接失败 | 捕获异常，返回空字典，前端显示"查询失败" |
| API 返回非 JSON | 解析失败，返回空字典，记录错误日志 |
| JSON 格式不符合预期 | 提取有效字段，缺失字段使用默认值 |

### 数据验证

| 场景 | 处理策略 |
|------|----------|
| 输入空单词 | 前端禁用查询按钮，后端返回错误 |
| 输入非英文单词 | DeepSeek 自动处理，可能返回不相关结果 |
| 保存时未选择分类 | 使用默认分类"单词"（如果存在） |
| 编辑他人单词 | 后端过滤查询集，前端显示"单词不存在" |

### 兼容性问题

| 场景 | 处理策略 |
|------|----------|
| 用户无 DeepSeekConfig 记录 | 自动创建默认配置 |
| 百度翻译和 DeepSeek 数据格式差异 | 统一转换为百度格式 |
| Google TTS 无法访问 | 保留 URL，用户可手动替换为其他 TTS 服务 |
| 旧单词无音标字段 | 前端判断字段是否存在，动态显示 |

### 前端交互

| 场景 | 处理策略 |
|------|----------|
| 查询超时 | 设置合理的超时时间（如 30 秒），超时后显示"查询超时" |
| 重复点击查询按钮 | 点击后禁用按钮，防止重复提交 |
| 保存时单词已存在 | 后端检查唯一性，返回错误提示 |
| 删除时取消操作 | 显示确认对话框，只有确认后才执行删除 |

## 测试验证

### 单元测试

#### 测试文件：`test_deepseek.py`

```python
def test_api_keys():
    """测试 API Key 配置"""
    assert check_deepseek_keys() == True

def test_api_call():
    """测试 API 调用"""
    result = call_deepseek_api("apple")
    assert 'phonetic' in result
    assert 'parts_and_means' in result
    assert 'src_tts' in result

def test_json_parsing():
    """测试 JSON 解析"""
    # 测试标准 JSON
    assert parse_json_response('{"key": "value"}') == {"key": "value"}

    # 测试带 markdown 标记的 JSON
    assert parse_json_response('```json\n{"key": "value"}\n```') == {"key": "value"}

def test_format_conversion():
    """测试格式转换"""
    deepseek_data = {
        "uk_phonetic": "/uk/",
        "us_phonetic": "/us/",
        "meaning": "测试",
        "example_sentences": [{"english": "Test", "chinese": "测试"}]
    }

    result = parse_deepseek_to_baidu_format(deepseek_data, "test")
    assert result["phonetic"] == ["uk", "us"]
    assert "简明释义: 测试" in result["simple_meaning"][0]
```

### 手动测试用例

#### 1. 基本查询流程

**步骤**：
1. 启动服务器：`python manage.py runserver`
2. 访问 http://127.0.0.1:8000/
3. 点击"DeepSeek Query"
4. 输入单词"hello"
5. 点击"查询"

**预期结果**：
- 显示单词"hello"
- 显示英式音标和美式音标
- 显示中文释义
- 显示 2-3 个例句（英文 + 中文翻译）
- TTS 播放按钮可点击播放

#### 2. 保存到单词本

**步骤**：
1. 在查询结果页点击"保存到单词本"
2. 选择分类（如"单词"）
3. 点击确认

**预期结果**：
- 显示"保存成功"提示
- 跳转到单词详情页
- 所有字段（音标、释义、TTS）正确显示

#### 3. AI 配置修改

**步骤**：
1. 访问"AI Settings"页面
2. 修改温度为 1.5
3. 修改系统提示词为自定义版本
4. 点击"保存配置"

**预期结果**：
- 显示"配置已保存"提示
- 下次查询时使用新配置
- 查询结果反映温度和提示词的变化（更创意化的输出）

#### 4. 单词编辑和 DeepSeek 导入

**步骤**：
1. 进入某个单词的详情页
2. 点击"编辑"按钮
3. 点击"导入 DeepSeek"按钮

**预期结果**：
- 显示"正在查询 DeepSeek API..."提示
- 自动填充释义、音标、TTS URL 字段
- 提示"导入成功！"

#### 5. 单词删除

**步骤**：
1. 进入某个单词的详情页
2. 点击"删除"按钮
3. 在确认对话框中点击"确认"

**预期结果**：
- 显示"单词已删除"提示
- 跳转到单词列表页
- 该单词不再出现在列表中

### 性能测试

| 指标 | 测试方法 | 预期值 |
|------|---------|-------|
| API 响应时间 | 查询单词 100 次，计算平均时间 | < 3 秒 |
| 并发查询 | 10 个用户同时查询 | 无错误，响应时间 < 5 秒 |
| 数据库查询 | 保存 1000 个单词后查询 | < 100ms |
| 前端渲染 | 显示 100 个单词的列表 | < 1 秒 |

## 性能影响

### API 调用

- **单次查询延迟**：2-3 秒（取决于 DeepSeek API 响应速度）
- **缓存机制**：当前未实现，未来可考虑 Redis 缓存常用单词
- **并发限制**：受 DeepSeek API 速率限制影响（需查看 API 文档）

### 数据库

- **新增表**：1 个（`EAW_deepseekconfig`）
- **表大小**：每个用户约 1 KB（假设提示词 500 字符）
- **查询性能**：`OneToOneField` 确保查询效率 O(1)

### 前端

- **页面大小**：新增约 50 KB（包含模板和静态资源）
- **JavaScript 性能**：AJAX 请求异步处理，不阻塞 UI
- **用户体验**：加载动画和进度提示优化等待体验

### 优化建议

1. **实现缓存**：对常用单词（如 Top 1000）进行本地缓存
2. **批量查询**：支持一次查询多个单词，减少 API 调用次数
3. **预加载**：在复习页面预加载即将复习单词的释义
4. **异步任务**：使用 Celery 将 API 调用改为异步，避免阻塞请求

## 未来扩展

### 1. 多模型支持

- 支持 `deepseek-coder`（代码生成模型）
- 支持 DeepSeek 未来推出的新模型
- 用户可选择不同的模型用于不同场景

### 2. 高级功能

- **例句难度分级**：根据用户水平生成不同难度的例句
- **记忆曲线集成**：根据艾宾浩斯遗忘曲线智能推荐复习时间
- **语音识别**：集成语音识别 API，支持口语练习
- **智能分类**：使用 AI 自动为单词分配分类标签

### 3. 多语言支持

- 支持其他语言（如日语、法语、德语）
- 用户可选择源语言和目标语言
- 自动检测输入语言

### 4. 社区功能

- 分享自定义提示词
- 分享高质量例句
- 评分和评论机制

### 5. 数据分析

- 统计用户查询的单词分布
- 分析学习进度和薄弱环节
- 生成个性化学习报告

## 相关文件

### 后端核心文件

| 文件路径 | 说明 | 变更类型 |
|---------|------|---------|
| `EAW/deepseek.py` | DeepSeek API 客户端模块 | 新增 |
| `EAW/models.py` | 数据库模型（新增 DeepSeekConfig） | 修改 |
| `EAW/views.py` | 视图函数（新增 DeepSeek 相关视图） | 修改 |
| `EAW/forms.py` | 表单类（新增 DeepSeekConfigForm） | 修改 |
| `EAW/utils.py` | 工具函数（新增 fetch_and_merge_deepseek） | 修改 |
| `EAW/urls.py` | URL 路由配置 | 修改 |
| `EAW/migrations/0009_deepseekconfig.py` | 数据库迁移文件 | 新增 |
| `EbbinghausAnywhere/settings.py` | 项目配置（API 密钥） | 修改 |
| `requirements.txt` | 依赖包列表 | 修改 |

### 前端模板文件

| 文件路径 | 说明 | 变更类型 |
|---------|------|---------|
| `EAW/templates/deepseek_query.html` | DeepSeek 查询页面 | 新增 |
| `EAW/templates/deepseek_config.html` | AI 配置页面 | 新增 |
| `EAW/templates/item_detail.html` | 单词详情页（UI 优化） | 修改 |
| `EAW/templates/item_form.html` | 单词编辑表单 | 新增 |
| `EAW/templates/item_confirm_delete.html` | 删除确认页面 | 新增 |
| `EAW/templates/home_logged_in.html` | 首页（新增入口卡片） | 修改 |

### 静态资源文件

| 文件路径 | 说明 | 变更类型 |
|---------|------|---------|
| `static/css/styles.css` | 样式表（新增卡片样式） | 修改 |

### 文档和配置

| 文件路径 | 说明 | 变更类型 |
|---------|------|---------|
| `DEEPSEEK_GUIDE.md` | DeepSeek API 使用指南 | 新增 |
| `.vscode/launch.json` | VS Code 调试配置 | 新增 |
| `test_deepseek.py` | 单元测试文件 | 新增 |

## 提交记录

### PR 合并提交

```
commit c122ad32d5f29c796b3198e5f6cbaf190b449f22
Merge: c5080d3 c3151e2
Author: Hui Qiao <35207458+myGitToy@users.noreply.github.com>
Date:   Sun Feb 1 13:46:06 2026 +0800

    Merge pull request #1 from myGitToy/feat_deepseek_claude4.5

    Feat deepseek claude4.5
```

### 功能开发提交

```
commit 97e7fc511e644a054dce42298b5a6b8c82e8e62d
Author: myGitToy
Date:   2026-02-01

    deepseek翻译的第一版，基本完成设想的架构和UI

    - 新增 DeepSeek API 集成
    - 实现查询页面和配置页面
    - 添加 TTS 播放功能
    - 实现一键保存到单词本

commit 1b8c7de9a9b0eff3c69bef35006967937adac9ec
Author: myGitToy
Date:   2026-02-01

    修改单词卡片中的UI呈现方式，保持和deepseek查询页面中一致

    - 统一卡片样式
    - 优化音标显示
    - 改进例句排版

commit a245b45977af6d87c74b2458b530523175290792
Author: myGitToy
Date:   2026-02-01

    增加单词卡片的删改查功能

    - 新增 ItemUpdateView
    - 新增 ItemDeleteView
    - 添加编辑和删除按钮
    - 实现权限控制

commit 1f6d9b656f5b76f2a5a753279f97c9342eabcca1
Author: myGitToy
Date:   2026-02-01

    增加在单词卡中能一键导入deepseek释义的功能

    - 在编辑页面添加"导入 DeepSeek"按钮
    - 实现 AJAX 调用自动填充表单
    - 添加加载提示和错误处理

commit 60e735fb2a3f406358bd42a4b3ad7b0f2cbb810d
Author: myGitToy
Date:   2026-02-01

    修正详细信息交互按钮可以展开，无法折叠的问题

    - 修复折叠按钮状态管理
    - 改进 Bootstrap Collapse 组件使用

commit c3151e2938a6fb6d31425f01eeb625df41c49aa9
Author: myGitToy
Date:   2026-02-01

    修复一键导入deepseek中需要用户二次确认，且无TTS链接的问题

    - 移除导入时的二次确认对话框
    - 自动生成并填充 TTS URL
    - 优化用户交互流程
```

## 版本信息

- **创建日期**：2026-02-01
- **功能分支**：feat_deepseek_claude4.5
- **目标分支**：main
- **合并状态**：✅ 已合并
- **合并日期**：2026-02-01
- **合并提交**：c122ad3
- **关联需求**：EbbinghausAnywhere 功能增强 - AI 驱动单词学习
- **影响范围**：后端 API、前端 UI、数据库模型
- **向后兼容**：完全兼容，保留原有百度翻译功能

---

**维护者**：Hui Qiao (myGitToy)
**审核状态**：已审核
**最后更新**：2026-02-10
