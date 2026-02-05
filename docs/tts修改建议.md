音标 TTS 多种播放方式扩展计划
一、需求澄清
根据用户确认，需要支持 4 种播放方式：

Google TTS - 美式（动态生成 URL）
Google TTS - 英式（动态生成 URL）
浏览器 Web Speech API - 美式（代码调用）
浏览器 Web Speech API - 英式（代码调用）
重要说明：

Google TTS 和浏览器 TTS 都不需要在数据库中存储任何信息
只需在前端添加播放按钮和对应的 JavaScript 函数
数据库模型无需修改
二、当前状态分析
2.1 数据库设计（EAW/models.py - Item 模型）
现有字段（保持不变）：

uk_phonetic: 英式音标（CharField，最大长度200）
us_phonetic: 美式音标（CharField，最大长度200）
src_tts: TTS 音频 URL（URLField，主要用于 Baidu API 等预生成的音频）
2.2 前端 TTS 实现
当前实现：

item_detail.html：只有 Google TTS 播放功能
playAudio(word, 'us') → Google TTS 美式
playAudio(word, 'uk') → Google TTS 英式
缺少的功能：

浏览器 Web Speech API 的播放按钮
清晰区分 Google TTS 和浏览器 TTS 的 UI
2.3 浏览器 Web Speech API 说明
这是浏览器内置的语音合成 API
没有 URL，直接通过 JavaScript 调用
使用 speechSynthesis.speak() 方法
可以设置语音、语速、音调等参数
完全免费，离线可用
三、设计方案
3.1 UI 布局设计
方案 A：全局设置 + 动态显示（推荐）
全局设置区域（在页面顶部或侧边栏）：


<div class="tts-preference mb-3">
    <label for="tts-method-select">
        <i class="fa fa-cog"></i> 默认发音方式：
    </label>
    <select id="tts-method-select" class="form-select form-select-sm" style="width: auto; display: inline-block;">
        <option value="google">🔊 Google TTS（在线，音质好）</option>
        <option value="browser">🎧 浏览器 TTS（离线，稳定）</option>
    </select>
    <small class="text-muted">
        切换后下方播放按钮将自动调整
    </small>
</div>
音标显示区域（根据选择动态显示）：


【当选择 Google 时】
美 [/əˈmerɪkən/]
  [🔊 播放发音]

英 [/brɪˈtɪʃ/]
  [🔊 播放发音]

【当选择浏览器时】
美 [/əˈmerɪkən/]
  [🎧 播放发音]

英 [/brɪˈtɪʃ/]
  [🎧 播放发音]
方案 B：两个按钮都显示（备选）

美 [/əˈmerɪkən/]
  [🔊 Google] [🎧 浏览器]

英 [/brɪˈtɪʃ/]
  [🔊 Google] [🎧 浏览器]
推荐使用方案 A，界面更简洁，用户只需选择一次即可。

3.2 JavaScript 函数设计
1. Google TTS 播放函数（已有，保留）

function playAudioWithGoogle(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);
    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('Google TTS播放失败:', error);
    });
}
2. 浏览器 TTS 播放函数（新增）

function playAudioWithBrowser(word, accent) {
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }

    // 停止当前播放
    window.speechSynthesis.cancel();

    var utterance = new SpeechSynthesisUtterance(word);
    var lang = accent === 'us' ? 'en-US' : 'en-GB';
    utterance.lang = lang;

    // 可选：设置语速和音调
    utterance.rate = 0.9;  // 语速（0.1-2.0）
    utterance.pitch = 1.0;  // 音调（0-2.0）

    // 尝试选择匹配的语音
    var voices = window.speechSynthesis.getVoices();
    var matchingVoice = voices.find(function(voice) {
        return voice.lang === lang;
    });
    if (matchingVoice) {
        utterance.voice = matchingVoice;
    }

    window.speechSynthesis.speak(utterance);
}
3.2 JavaScript 函数设计
1. TTS 偏好管理

// 获取用户偏好（默认 Google）
function getTTSPreference() {
    return localStorage.getItem('tts_preference') || 'google';
}

// 保存用户偏好
function setTTSPreference(method) {
    localStorage.setItem('tts_preference', method);
    console.log('TTS 偏好已设置为:', method);
}

// 智能播放函数（根据偏好自动选择）
function playAudio(word, accent) {
    const method = getTTSPreference();

    if (method === 'browser') {
        playAudioWithBrowser(word, accent);
    } else {
        playAudioWithGoogle(word, accent);
    }
}
2. Google TTS 播放函数

function playAudioWithGoogle(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);
    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('Google TTS播放失败:', error);
        alert('Google TTS 播放失败，请尝试切换到浏览器 TTS 模式');
    });
}
3. 浏览器 TTS 播放函数

function playAudioWithBrowser(word, accent) {
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }

    // 停止当前播放
    window.speechSynthesis.cancel();

    var utterance = new SpeechSynthesisUtterance(word);
    var lang = accent === 'us' ? 'en-US' : 'en-GB';
    utterance.lang = lang;

    // 设置语速和音调
    utterance.rate = 0.9;
    utterance.pitch = 1.0;

    // 尝试选择匹配的语音
    var voices = window.speechSynthesis.getVoices();
    var matchingVoice = voices.find(function(voice) {
        return voice.lang === lang;
    });
    if (matchingVoice) {
        utterance.voice = matchingVoice;
    }

    window.speechSynthesis.speak(utterance);
}
四、实施步骤
步骤 1：修改 item_detail.html
1.1 添加 TTS 偏好选择器
在页面顶部（卡片头部或内容区域开始处）添加：


<!-- TTS 偏好设置 -->
<div class="mb-3 p-2 bg-light rounded">
    <div class="d-flex align-items-center">
        <label for="tts-method-select" class="me-2 mb-0">
            <i class="fa fa-cog text-primary"></i> 默认发音方式：
        </label>
        <select id="tts-method-select" class="form-select form-select-sm" style="width: auto;">
            <option value="google">🔊 Google TTS（在线，音质好）</option>
            <option value="browser">🎧 浏览器 TTS（离线，稳定）</option>
        </select>
        <small class="text-muted ms-2">
            <i class="fa fa-info-circle"></i> 切换后下方播放按钮将自动调整
        </small>
    </div>
</div>
1.2 修改音标显示区域
当前代码（第 26-56 行）：

当前代码（第 26-56 行）：


<!-- 音标和发音 -->
{% if object.category.name == '单词' %}
    {% if object.uk_phonetic or object.us_phonetic or object.src_tts %}
        <div class="mb-3">
            <h6><i class="fa fa-volume-up"></i> 发音</h6>
            <div>
                <!-- 美式发音 -->
                {% if object.us_phonetic %}
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-info me-2">美 [{{ object.us_phonetic }}]</span>
                        <button class="btn btn-sm btn-outline-primary" onclick="playAudio('{{ object.item }}', 'us')">
                            <i class="fa fa-play"></i> 播放发音
                        </button>
                    </div>
                {% endif %}
                <!-- 英式发音 -->
                {% if object.uk_phonetic %}
                    <div class="d-flex align-items-center">
                        <span class="badge bg-info me-2">英 [{{ object.uk_phonetic }}]</span>
                        <button class="btn btn-sm btn-outline-primary" onclick="playAudio('{{ object.item }}', 'uk')">
                            <i class="fa fa-play"></i> 播放发音
                        </button>
                    </div>
                {% endif %}
            </div>
        </div>
    {% endif %}
{% endif %}
修改为：


<!-- 音标和发音 -->
{% if object.category.name == '单词' %}
    {% if object.uk_phonetic or object.us_phonetic %}
        <div class="mb-3">
            <h6><i class="fa fa-volume-up"></i> 发音</h6>
            <div>
                <!-- 美式发音 -->
                {% if object.us_phonetic %}
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-info me-2" style="min-width: 150px;">美 [{{ object.us_phonetic }}]</span>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="playAudioWithGoogle('{{ object.item }}', 'us')" title="Google TTS 美式发音">
                            <i class="fa fa-google"></i> Google
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="playAudioWithBrowser('{{ object.item }}', 'us')" title="浏览器 TTS 美式发音">
                            <i class="fa fa-headphones"></i> 浏览器
                        </button>
                    </div>
                {% endif %}
                <!-- 英式发音 -->
                {% if object.uk_phonetic %}
                    <div class="d-flex align-items-center">
                        <span class="badge bg-info me-2" style="min-width: 150px;">英 [{{ object.uk_phonetic }}]</span>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="playAudioWithGoogle('{{ object.item }}', 'uk')" title="Google TTS 英式发音">
                            <i class="fa fa-google"></i> Google
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="playAudioWithBrowser('{{ object.item }}', 'uk')" title="浏览器 TTS 英式发音">
                            <i class="fa fa-headphones"></i> 浏览器
                        </button>
                    </div>
                {% endif %}
            </div>
        </div>
    {% endif %}
{% endif %}
更新 JavaScript 部分（第 262-272 行）：


// 保留原有的 playAudio 函数（重命名为 playAudioWithGoogle）
function playAudioWithGoogle(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);
    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('Google TTS播放失败:', error);
        alert('Google TTS 播放失败，可能是网络问题或浏览器限制');
    });
}

// 新增：浏览器 Web Speech API 播放函数
function playAudioWithBrowser(word, accent) {
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }

    // 停止当前播放
    window.speechSynthesis.cancel();

    var utterance = new SpeechSynthesisUtterance(word);
    var lang = accent === 'us' ? 'en-US' : 'en-GB';
    utterance.lang = lang;

    // 设置语速和音调
    utterance.rate = 0.9;
    utterance.pitch = 1.0;

    // 尝试选择匹配的语音
    var voices = window.speechSynthesis.getVoices();
    var matchingVoice = voices.find(function(voice) {
        return voice.lang === lang;
    });
    if (matchingVoice) {
        utterance.voice = matchingVoice;
    }

    window.speechSynthesis.speak(utterance);
}

// 保持向后兼容：保留原有的 playAudio 函数作为别名
function playAudio(word, accent) {
    playAudioWithGoogle(word, accent);
}
步骤 2：更新 JavaScript 初始化逻辑
在 DOMContentLoaded 事件中添加：


document.addEventListener('DOMContentLoaded', function() {
    // 初始化 TTS 偏好选择器
    const ttsSelect = document.getElementById('tts-method-select');
    if (ttsSelect) {
        // 设置当前值
        ttsSelect.value = getTTSPreference();

        // 监听变化
        ttsSelect.addEventListener('change', function() {
            const newMethod = this.value;
            setTTSPreference(newMethod);

            // 更新播放按钮图标和标题
            updatePlayButtons(newMethod);
        });
    }

    // 初始化语音库
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = function() {
            console.log('语音列表已加载');
        };
    }
});

// 更新播放按钮外观
function updatePlayButtons(method) {
    const playButtons = document.querySelectorAll('[onclick^="playAudio"]');
    const googleIcon = '<i class="fa fa-google"></i>';
    const browserIcon = '<i class="fa fa-headphones"></i>';
    const icon = method === 'google' ? googleIcon : browserIcon;

    playButtons.forEach(function(button) {
        const iconElement = button.querySelector('i');
        if (iconElement) {
            iconElement.className = method === 'google' ? 'fa fa-google' : 'fa fa-headphones';
        }
    });
}
步骤 3：修改 deepseek_query.html
在查询结果页面添加相同的 TTS 偏好选择器和逻辑。

步骤 4：修改 review_day.html
在复习页面添加 TTS 偏好选择器（第 116-128 行区域）。

在查询结果页面也添加浏览器 TTS 播放按钮，与 item_detail.html 类似。

步骤 3：修改 review_day.html
在复习页面添加浏览器 TTS 播放选项（第 116-128 行区域）。

步骤 4：添加语音库初始化（可选优化）
为了确保浏览器语音库已加载，可以在页面加载时预加载语音列表：


// 在 DOMContentLoaded 中添加
if ('speechSynthesis' in window) {
    // 预加载语音列表
    window.speechSynthesis.getVoices();
    // 监听语音列表变化
    window.speechSynthesis.onvoiceschanged = function() {
        console.log('语音列表已加载');
    };
}
步骤 5：测试和验证
五、关键文件清单
需要修改的文件：

EAW/templates/item_detail.html - 主要修改点

添加 TTS 偏好选择器（页面顶部）
更新音标显示区域的 HTML（第 26-56 行）
更新 JavaScript 函数和初始化逻辑
EAW/templates/deepseek_query.html - 查询结果页

添加 TTS 偏好选择器
添加 playAudioWithBrowser 函数
更新播放按钮调用逻辑
EAW/templates/review_day.html - 复习页面

添加 TTS 偏好选择器（第 116-128 行区域）
更新播放逻辑
不需要修改的文件：

EAW/models.py - 数据库模型保持不变
EAW/views.py - 后端逻辑不需要修改
EAW/forms.py - 表单不需要修改
数据库迁移文件 - 不需要
六、验证测试
测试点
1. 功能测试
 TTS 偏好选择器：下拉框正确显示两个选项
 默认选择：默认选中 Google TTS
 切换功能：切换到浏览器 TTS 后，播放按钮图标更新
 偏好记忆：刷新页面后，选择器保持上次选择
 Google TTS 播放：选择 Google 时，点击播放正常工作
 浏览器 TTS 播放：选择浏览器时，点击播放正常工作
 美式/英式切换：两种口音都能正常播放
2. UI 测试
 选择器样式美观，位置合理
 音标正确显示（美式和英式）
 播放按钮图标根据选择动态变化
 按钮提示文字（title）正确
3. 兼容性测试
 Chrome/Edge：所有功能正常
 Firefox：所有功能正常
 Safari：所有功能正常（如有 Mac 可测试）
4. 持久化测试
 刷新页面后，选择器保持上次选择
 关闭标签页后重新打开，选择器保持上次选择
 清除浏览器数据后，恢复默认 Google TTS
5. 回归测试
 旧的播放方式仍能正常工作
 现有数据不受影响
 src_tts 字段仍能正常使用（如果有的话）
测试方法
手动测试：

访问单词详情页
切换 TTS 偏好选择器
点击播放按钮验证功能
刷新页面验证持久化
浏览器控制台：

打开开发者工具
检查 localStorage 中是否保存了偏好
查看是否有 JavaScript 错误
跨浏览器测试：

在不同浏览器中测试
确保兼容性
需要修改的文件：

EAW/templates/item_detail.html - 主要修改点

更新音标显示区域的 HTML（第 26-56 行）
更新 JavaScript 函数（第 262-272 行）
EAW/templates/deepseek_query.html - 查询结果页

添加浏览器 TTS 播放按钮
添加 playAudioWithBrowser 函数
EAW/templates/review_day.html - 复习页面

添加浏览器 TTS 播放选项（第 116-128 行区域）
static/tts-test.html - 已有的测试页面（不需要修改）

不需要修改的文件：

EAW/models.py - 数据库模型保持不变
EAW/views.py - 后端逻辑不需要修改
EAW/forms.py - 表单不需要修改
数据库迁移文件 - 不需要
六、验证测试
测试点
1. 功能测试
 Google TTS - 美式：点击按钮能正常播放美式发音
 Google TTS - 英式：点击按钮能正常播放英式发音
 浏览器 TTS - 美式：点击按钮能正常播放美式发音
 浏览器 TTS - 英式：点击按钮能正常播放英式发音
2. UI 测试
 音标正确显示（美式和英式）
 4 个播放按钮正确显示
 按钮样式美观，布局合理
 图标正确显示（Google 和浏览器图标）
3. 兼容性测试
 Chrome/Edge：所有功能正常
 Firefox：所有功能正常
 Safari：所有功能正常（如有 Mac 可测试）
4. 错误处理
 Google TTS 失败时有提示
 浏览器不支持 Web Speech API 时有提示
 网络断开时 Google TTS 失败，但浏览器 TTS 仍可用
5. 回归测试
 旧的播放方式仍能正常工作（playAudio 函数）
 现有数据不受影响
 src_tts 字段仍能正常使用（如果有的话）
测试方法
手动测试：

访问单词详情页
点击 4 个播放按钮
验证每个按钮都能正常播放
浏览器控制台：

打开浏览器开发者工具
查看是否有 JavaScript 错误
检查网络请求（Google TTS）
跨浏览器测试：

在不同浏览器中测试
确保兼容性
七、注意事项
7.1 Google TTS 限制
Google TTS 是非官方 API，可能随时失效
需要网络连接
可能有频率限制
7.2 浏览器 Web Speech API 限制
不同浏览器的语音库不同
首次加载可能需要等待语音库初始化
某些移动浏览器支持有限
语音质量因设备和浏览器而异
7.3 用户体验建议
提供两种方式让用户选择
如果一种方式失败，用户可以尝试另一种
未来可以考虑添加用户偏好设置，记住用户的选择
7.4 性能考虑
Google TTS 每次都发起网络请求
浏览器 TTS 完全本地，性能更好
可以考虑优先使用浏览器 TTS，失败时回退到 Google TTS
八、未来扩展方向
如果需要进一步扩展，可以考虑：

用户偏好设置：

记住用户喜欢使用的 TTS 方式
允许用户自定义语速和音调
更多 TTS 源：

添加其他在线 TTS 服务（如 Baidu、Azure、AWS 等）
添加更多口音（如澳式、加式等）
TTS 质量对比：

让用户对不同 TTS 源进行评分
根据评分推荐最佳 TTS 源
离线支持：

优先使用浏览器 TTS（完全离线）
缓存 Google TTS 音频（如果政策允许）
User approved the plan
完美！计划已批准。让我给你一个清晰的实施总结：

📋 TTS 偏好选择器功能 - 实施总结
🎯 核心目标
在现有 feat_tts 分支上添加一个 TTS 偏好选择器，让用户可以在 Google TTS 和浏览器 TTS 之间切换。

✅ 关键确认
项目	状态	说明
开发分支	✅ feat_tts	安全，不影响生产
生产分支	main	未部署 TTS 功能
数据库修改	❌ 不需要	保持现有字段
src_tts 字段	✅ 保留	继续存储，不删除
📝 实施方案总结
方案选择：方案 A - 全局设置 + 两个按钮都显示
UI 布局：


┌─────────────────────────────────────┐
│ 🔊 默认发音方式： [Google TTS ▼]  │  ← 全局选择器
├─────────────────────────────────────┤
│                                   │
│  美 [/əˈmerɪkən/]                  │
│    [🔊 Google] [🎧 浏览器]         │  ← 两个按钮
│                                   │
│  英 [/brɪˈtɪʃ/]                  │
│    [🔊 Google] [🎧 浏览器]         │  ← 两个按钮
└─────────────────────────────────────┘
用户行为：

在顶部选择器选择默认方式（Google 或浏览器）
两个按钮都显示，让用户可以随时切换
选择器状态保存到 localStorage（持久化）
🔧 需要修改的文件（3个）
1. EAW/templates/item_detail.html - 主要修改
添加内容：

TTS 偏好选择器（页面顶部）
浏览器 TTS 播放按钮
playAudioWithBrowser() 函数
getTTSPreference() / setTTSPreference() 函数
选择器初始化逻辑
2. EAW/templates/deepseek_query.html - 同样逻辑
3. EAW/templates/review_day.html - 同样逻辑
💻 JavaScript 核心函数（3个）

// 1. TTS 偏好管理
function getTTSPreference() {
    return localStorage.getItem('tts_preference') || 'google';
}

function setTTSPreference(method) {
    localStorage.setItem('tts_preference', method);
}

// 2. Google TTS 播放（已有，保留）
function playAudioWithGoogle(word, accent) {
    var tl = accent === 'us' ? 'en-US' : 'en-GB';
    var audioUrl = 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=' + tl + '&q=' + encodeURIComponent(word);
    var audio = new Audio(audioUrl);
    audio.play().catch(function(error) {
        console.error('Google TTS播放失败:', error);
        alert('Google TTS 播放失败，请尝试切换到浏览器 TTS 模式');
    });
}

// 3. 浏览器 TTS 播放（新增）
function playAudioWithBrowser(word, accent) {
    if (!('speechSynthesis' in window)) {
        alert('您的浏览器不支持语音合成功能');
        return;
    }
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = accent === 'us' ? 'en-US' : 'en-GB';
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

// 4. 智能播放（根据偏好选择）
function playAudio(word, accent) {
    const method = getTTSPreference();
    if (method === 'browser') {
        playAudioWithBrowser(word, accent);
    } else {
        playAudioWithGoogle(word, accent);
    }
}
📂 实施步骤
Step 1：修改 item_detail.html
添加 TTS 偏好选择器
为美式/英式音标各添加两个播放按钮
添加 JavaScript 函数和初始化逻辑
Step 2：修改 deepseek_query.html
同样的逻辑
Step 3：修改 review_day.html
同样的逻辑
Step 4：本地测试
运行 python manage.py runserver
访问单词详情页
测试切换和播放功能
Step 5：提交和部署

git add .
git commit -m "添加 TTS 偏好选择器功能

- 添加全局 TTS 方式选择器
- 新增浏览器 Web Speech API 支持
- 用户偏好自动保存到 localStorage
- 默认使用 Google TTS，可切换到浏览器 TTS"

# 完成后合并到 main
git checkout main
git pull origin main
git merge feat_tts
git push origin main
⚠️ 关键注意事项
保留 src_tts 字段：不要删除，保持向后兼容
向后兼容：保留原有 playAudio() 函数作为别名
localStorage：偏好存储在浏览器本地，无服务器压力
测试充分：确保两种 TTS 方式都能正常工作
准备好开始实施了吗？ 我可以按照这个方案开始修改代码！