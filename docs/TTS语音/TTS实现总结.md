# TTS 实现总结（gpt5 mini code）

## 📊 数据模型与存储

### 1. **数据库字段定义**（`EAW/models.py`）

```python
# TTS 音频链接（可选，主要用于百度 API 返回的预生成链接）
src_tts = models.URLField(
    max_length=500, 
    null=True, 
    blank=True,
    help_text="URL pointing to the TTS audio file (e.g., Baidu API TTS)"
)

# 美式音标
us_phonetic = models.CharField(
    max_length=200, 
    null=True, 
    blank=True, 
    help_text="American Phonetic (optional)"
)

# 英式音标
uk_phonetic = models.CharField(
    max_length=200, 
    null=True, 
    blank=True, 
    help_text="British Phonetic (optional)"
)
```

**存储模式**：
- ✅ 只存储 URL 链接和音标文本
- ❌ **不存储音频文件本身**

---

## 🎵 TTS 实现方式

### 方式 1：**Google TTS（动态生成，主要使用）**

#### 🔹 实际播放机制（重要）

前端 `playAudio` 函数**动态生成** Google TTS URL，**不依赖** `src_tts` 字段：

**`EAW/templates/item_detail.html` (line 263-273)**：
```javascript
function playAudio(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    // ⚠️ 注意：此处动态生成 URL，不使用数据库中的 src_tts
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);
    
    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('播放失败:', error);
        alert('音频播放失败，可能是网络问题或浏览器限制');
    });
}
```

**调用方式**：
```html
<!-- src_tts 字段仅用于判断是否显示播放按钮 -->
{% if object.src_tts %}
    <button onclick="playAudio('{{ object.item }}', 'us')">
        <i class="fa fa-play"></i> 播放发音
    </button>
{% endif %}
```

#### 🔹 src_tts 字段的实际作用

虽然代码中会保存 Google TTS 链接到 `src_tts`，但**实际播放时不使用该字段**：

1. **DeepSeek 查询保存**（`EAW/views.py` line 1560）
```python
# 保存到数据库，但播放时不使用
src_tts=f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}"
```

2. **Item 编辑页面自动填充**（`EAW/templates/item_form.html` line 144）
```javascript
// 表单编辑时自动填充，但播放时重新生成
srcTtsField.value = `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q=${encodeURIComponent(word)}`;
```

---

### 方式 2：**百度翻译 API TTS（预生成链接）**

#### 🔹 获取方式

**`EAW/translate.py` (line 78-82)**：
```python
# 从百度 API 响应中提取 TTS URL
src_tts = trans_result.get('src_tts', None)

# 验证 URL 安全性
if src_tts and not is_valid_tts_url(src_tts):
    print(f"无效的 TTS URL: {src_tts}")
    src_tts = None
```

#### 🔹 URL 安全验证

**`EAW/translate.py` (line 221-231)**：
```python
def is_valid_tts_url(url):
    """验证音频链接的有效性和安全性"""
    if not url.startswith("https://"):
        return False
    # ⚠️ 注意：仅允许百度域名
    if re.search(r"baidu\.com", url):
        return True
    return False
```

**问题**：此验证函数只允许百度 TTS，但 Google TTS 在前端播放时不经过此验证。

---

### 方式 3：**浏览器 Web Speech API（测试功能）**

#### 🔹 独立测试页面

**`static/tts-test.html`** 实现了完整的浏览器原生 TTS 功能：

```javascript
// 使用浏览器内置的语音合成 API
const utterance = new SpeechSynthesisUtterance(word);
utterance.lang = 'en-US';  // 或 'en-GB'
utterance.rate = 1.0;      // 语速
utterance.pitch = 1.0;     // 音调

speechSynthesis.speak(utterance);
```

**特点**：
- ✅ 完全离线，不依赖网络
- ✅ 支持多种语言和声音选择
- ✅ 可调节语速、音调、音量
- ❌ 音质依赖浏览器和操作系统
- ❌ 未集成到主应用中（仅作为测试页面）

---

## 🔊 播放方式对比
清单

### 核心实现
- **`EAW/models.py`** - 数据模型定义（src_tts, us_phonetic, uk_phonetic）
- **`EAW/templates/item_detail.html`** - 详情页播放功能（动态 Google TTS）
- **`EAW/templates/deepseek_query.html`** - DeepSeek 查询页播放功能

### 辅助功能
- **`EAW/views.py`** - DeepSeek 查询中保存 TTS 链接（实际播放不使用）
- **`EAW/templates/item_form.html`** - 编辑页面自动填充 TTS 链接
- **`EAW/translate.py`** - 百度翻译 API 和 URL 安全验证

### 测试功能
- **`static/tts-test.html`** - Web Speech API 测试页面（独立功能）

---

## 🔧 改进建议

1. **简化 src_tts 使用**：考虑直接移除数据库保存，仅在前端动态生成
2. **统一 TTS 策略**：明确 Google/百度 TTS 的使用场景
3. **集成 Web Speech API**：可作为 Google TTS 的离线备选方案
4. **更新 URL 验证逻辑**：允许 Google TTS 域名通过验证

---

*文档生成日期：2026年2月5日*  
*最后更新：基于代码交叉检查修正
```plaintext
保存流程：DeepSeek/表单 → 生成 Google TTS URL → 保存到 src_tts
          ↓
显示流程：检查 src_tts 是否存在 → 显示播放按钮
          ↓
播放流程：点击按钮 → playAudio() → 忽略 src_tts → 动态生成新 URL → 播放
```

**结论**：`src_tts` 字段主要用于：
1. 判断是否显示播放按钮（存在性检查）
2. 存储百度 API 返回的预生成链接（但 Google TTS 播放时不使用）

---

## 🆚 技术总结

| 特性 | 实现方式 |
|------|---------|
| **存储方式** | URL 链接字符串 + 音标文本 |
| **文件存储** | ❌ 不存储音频文件 |
| **主要播放** | Google TTS（动态 URL） |
| **备用播放** | 百度 TTS（预生成链接） |
| **测试功能** | Web Speech API（离线） |
| **服务器角色** | 仅存储链接，不处理音频流 |
| **音标显示** | us_phonetic / uk_phonetic |

---

## 📝 优劣分析

### ✅ 优势

- 节省服务器存储和带宽
- Google TTS 音质较好
- 前端直接播放，无服务器压力
- 支持美式/英式发音切换

### ❌ 劣势

- Google TTS 在国内可能无法访问
- 完全依赖网络连接
- `src_tts` 字段设计存在冗余（存储了但不使用）
- URL 验证函数与实际使用不一致

---

## 📂 相关文件列表

- `EAW/models.py` - TTS URL 字段定义
- `EAW/views.py` - DeepSeek 查询中生成 TTS 链接
- `EAW/translate.py` - 百度翻译 API 和 URL 验证
- `EAW/templates/item_detail.html` - 详情页播放功能
- `EAW/templates/deepseek_query.html` - DeepSeek 查询页播放功能
- `EAW/templates/item_form.html` - 编辑页面自动生成 TTS 链接
- `static/tts-test.html` - TTS 测试页面

---

*文档生成日期：2026年2月5日*
