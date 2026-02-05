# TTS 功能代码实现参考

> **文档标识**：glm code
> **创建日期**：2026-02-05
> **用途**：TTS 功能代码实现参考

---

## 一、数据库模型

### 文件：`EAW/models.py`

```python
class Item(models.Model):
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

---

## 二、Google TTS 实现

### 方式 1：动态播放函数（主要使用）

#### 文件：`EAW/templates/item_detail.html`

**HTML 部分**（第 26-56 行）：
```html
<!-- 音标和发音 -->
{% if object.category.name == '单词' %}
    {% if object.uk_phonetic or object.us_phonetic %}
        <div class="mb-3">
            <h6><i class="fa fa-volume-up"></i> 发音</h6>
            <div>
                <!-- 美式发音 -->
                {% if object.us_phonetic %}
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-info me-2" style="min-width: 150px;">
                            美 [{{ object.us_phonetic }}]
                        </span>
                        <button class="btn btn-sm btn-outline-primary me-1"
                                onclick="playAudioWithGoogle('{{ object.item }}', 'us')"
                                title="Google TTS 美式发音">
                            <i class="fa fa-google"></i> Google
                        </button>
                        <button class="btn btn-sm btn-outline-secondary"
                                onclick="playAudioWithBrowser('{{ object.item }}', 'us')"
                                title="浏览器 TTS 美式发音">
                            <i class="fa fa-headphones"></i> 浏览器
                        </button>
                    </div>
                {% endif %}

                <!-- 英式发音 -->
                {% if object.uk_phonetic %}
                    <div class="d-flex align-items-center">
                        <span class="badge bg-info me-2" style="min-width: 150px;">
                            英 [{{ object.uk_phonetic }}]
                        </span>
                        <button class="btn btn-sm btn-outline-primary me-1"
                                onclick="playAudioWithGoogle('{{ object.item }}', 'uk')"
                                title="Google TTS 英式发音">
                            <i class="fa fa-google"></i> Google
                        </button>
                        <button class="btn btn-sm btn-outline-secondary"
                                onclick="playAudioWithBrowser('{{ object.item }}', 'uk')"
                                title="浏览器 TTS 英式发音">
                            <i class="fa fa-headphones"></i> 浏览器
                        </button>
                    </div>
                {% endif %}
            </div>
        </div>
    {% endif %}
{% endif %}
```

**JavaScript 部分**（第 263-273 行）：
```javascript
// Google TTS 播放函数
function playAudioWithGoogle(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);

    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('Google TTS播放失败:', error);
        alert('音频播放失败，可能是网络问题或浏览器限制');
    });
}

// 向后兼容：保留原有的 playAudio 函数
function playAudio(word, accent) {
    playAudioWithGoogle(word, accent);
}
```

---

### 方式 2：预加载音频元素

#### 文件：`EAW/templates/deepseek_query.html`

**HTML 部分**（第 180-200 行）：
```html
<!-- 音频元素 -->
<audio id="word-audio-us"></audio>
<audio id="word-audio-uk"></audio>

<!-- 播放按钮 -->
<button id="play-us-btn">
    <i class="fa fa-play"></i> 美式发音
</button>
<button id="play-uk-btn">
    <i class="fa fa-play"></i> 英式发音
</button>
```

**JavaScript 部分**（第 264-272 行）：
```javascript
// 设置音频源
const audioUS = document.getElementById('word-audio-us');
const audioUK = document.getElementById('word-audio-uk');
audioUS.src = `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en-US&q=${word}`;
audioUK.src = `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en-GB&q=${word}`;

// 播放事件
document.getElementById('play-us-btn').addEventListener('click', function() {
    audioUS.play().catch(error => {
        alert('音频播放失败，可能是网络问题或浏览器限制');
    });
});
```

---

## 三、浏览器 Web Speech API 实现

### 完整实现

```javascript
// 浏览器 TTS 播放函数
function playAudioWithBrowser(word, accent) {
    // 检查浏览器支持
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }

    // 停止当前播放
    window.speechSynthesis.cancel();

    // 创建语音实例
    var utterance = new SpeechSynthesisUtterance(word);
    var lang = accent === 'us' ? 'en-US' : 'en-GB';
    utterance.lang = lang;

    // 设置参数
    utterance.rate = 0.9;   // 语速（0.1-2.0）
    utterance.pitch = 1.0;  // 音调（0-2.0）
    utterance.volume = 1.0; // 音量（0-1.0）

    // 尝试选择匹配的语音
    var voices = window.speechSynthesis.getVoices();
    var matchingVoice = voices.find(function(voice) {
        return voice.lang === lang;
    });
    if (matchingVoice) {
        utterance.voice = matchingVoice;
    }

    // 播放
    window.speechSynthesis.speak(utterance);
}

// 初始化语音列表
if ('speechSynthesis' in window) {
    // 预加载语音列表
    window.speechSynthesis.getVoices();

    // 监听语音列表变化
    window.speechSynthesis.onvoiceschanged = function() {
        console.log('语音列表已加载，共', window.speechSynthesis.getVoices().length, '个语音');
    };
}
```

### 完整示例页面

参考：`static/tts-test.html`

---

## 四、后端实现

### DeepSeek 查询保存 TTS 链接

#### 文件：`EAW/views.py`（第 1560 行）

```python
# 保存 Google TTS 链接到数据库（注意：实际播放时不使用）
src_tts = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}"
```

### 百度翻译 API

#### 文件：`EAW/translate.py`（第 78-82 行）

```python
# 从百度 API 响应中提取 TTS URL
src_tts = trans_result.get('src_tts', None)

# 验证 URL 安全性
if src_tts and not is_valid_tts_url(src_tts):
    print(f"无效的 TTS URL: {src_tts}")
    src_tts = None
```

#### URL 验证函数（第 221-231 行）

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

### 表单自动填充

#### 文件：`EAW/templates/item_form.html`（第 144 行）

```javascript
// 自动填充 Google TTS 链接
const srcTtsField = document.querySelector('input[name="src_tts"]');
if (srcTtsField) {
    srcTtsField.value = `https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q=${encodeURIComponent(word)}`;
}
```

---

## 五、播放流程对比

### Google TTS 流程

```
用户点击按钮
    ↓
playAudioWithBrowser(word, 'us')
    ↓
动态生成 URL: https://translate.google.com/translate_tts?...&tl=en-US&q=word
    ↓
new Audio(url)
    ↓
audio.play()
    ↓
浏览器请求 Google TTS 服务
    ↓
流媒体播放
```

**特点**：
- ✅ 每次动态生成 URL
- ✅ 不依赖数据库中的 `src_tts`
- ❌ 需要网络连接
- ❌ Google 服务可能不稳定

### 浏览器 Web Speech API 流程

```
用户点击按钮
    ↓
playAudioWithBrowser(word, 'us')
    ↓
new SpeechSynthesisUtterance(word)
    ↓
设置参数（lang, rate, pitch）
    ↓
speechSynthesis.speak(utterance)
    ↓
浏览器本地合成语音
    ↓
播放
```

**特点**：
- ✅ 完全离线可用
- ✅ 无需网络连接
- ❌ 音质依赖浏览器和操作系统
- ❌ 不同浏览器语音库不同

---

## 六、关键技术点

### 1. Google TTS URL 格式

```
https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={语言代码}&q={单词}

参数说明：
- ie: 输入编码（UTF-8）
- client: 客户端标识（tw-ob）
- tl: 目标语言（en-US, en-GB, zh-CN 等）
- q: 要朗读的文本（需要 URL 编码）
```

### 2. Web Speech API 核心 API

```javascript
// 检查支持
'speechSynthesis' in window

// 获取语音列表
window.speechSynthesis.getVoices()

// 创建语音实例
new SpeechSynthesisUtterance(text)

// 播放
window.speechSynthesis.speak(utterance)

// 停止
window.speechSynthesis.cancel()

// 暂停
window.speechSynthesis.pause()

// 恢复
window.speechSynthesis.resume()
```

### 3. 语音对象属性

```javascript
utterance.lang = 'en-US';     // 语言
utterance.rate = 1.0;          // 语速（0.1-2.0）
utterance.pitch = 1.0;         // 音调（0-2.0）
utterance.volume = 1.0;        // 音量（0-1.0）
utterance.voice = voiceObject; // 指定语音
```

---

## 七、常见问题

### Q1: Google TTS 无法播放？

**可能原因**：
- 网络问题
- Google 服务被墙
- 浏览器限制自动播放

**解决方案**：
- 使用浏览器 Web Speech API 作为备选
- 添加用户交互触发（点击按钮）

### Q2: 浏览器 TTS 没有声音？

**可能原因**：
- 语音库未加载
- 不支持该语言

**解决方案**：
```javascript
// 预加载语音列表
window.speechSynthesis.getVoices();
window.speechSynthesis.onvoiceschanged = function() {
    console.log('语音列表已加载');
};
```

### Q3: 如何选择最佳 TTS 方式？

**推荐策略**：
1. **在线环境**：优先使用 Google TTS（音质好）
2. **离线环境**：使用浏览器 Web Speech API
3. **国内网络**：考虑百度 API 或浏览器 TTS

---

## 八、扩展建议

### 1. 添加用户偏好设置

```javascript
// 用户可以选择默认 TTS 方式
const userSettings = {
    ttsMethod: 'google', // 'google' | 'browser' | 'auto'
    rate: 0.9,
    pitch: 1.0
};
```

### 2. 添加更多语言支持

```javascript
const languages = {
    'en-US': '美式英语',
    'en-GB': '英式英语',
    'en-AU': '澳式英语',
    'zh-CN': '中文'
};
```

### 3. 添加错误重试机制

```javascript
function playWithRetry(word, accent, maxRetries = 2) {
    let retries = 0;

    function tryPlay() {
        playAudioWithGoogle(word, accent).catch(error => {
            if (retries < maxRetries) {
                retries++;
                setTimeout(tryPlay, 1000);
            } else {
                // 回退到浏览器 TTS
                playAudioWithBrowser(word, accent);
            }
        });
    }

    tryPlay();
}
```

---

## 九、文件清单

| 文件路径 | 用途 | 修改频率 |
|---------|------|----------|
| `EAW/models.py` | 数据模型定义 | 低 |
| `EAW/views.py` | 后端逻辑（保存链接） | 低 |
| `EAW/templates/item_detail.html` | 详情页播放功能 | 高 |
| `EAW/templates/deepseek_query.html` | 查询页播放功能 | 中 |
| `EAW/templates/review_day.html` | 复习页播放功能 | 中 |
| `EAW/templates/item_form.html` | 表单自动填充 | 低 |
| `EAW/translate.py` | 百度 API 集成 | 低 |
| `static/tts-test.html` | 测试页面 | 低 |

---

## 十、参考资源

- [Google TTS API](https://cloud.google.com/text-to-speech)
- [Web Speech API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)
- [百度翻译 API](http://api.fanyi.baidu.com/api/trans/product/apidoc)

---

**文档标识：glm code**
**最后更新：2026-02-05**
