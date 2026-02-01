# DeepSeek API 集成使用指南

## 📋 功能概述

成功集成 DeepSeek API 到 EbbinghausAnywhere 单词记忆系统，提供以下功能：

### ✨ 核心功能
1. **智能单词查询** - 使用 DeepSeek AI 获取单词释义、音标和例句
2. **个性化配置** - 支持自定义模型、温度参数和系统提示词
3. **一键保存** - 查询结果可直接保存到单词本
4. **TTS 音频播放** - 集成 Google TTS，点击播放单词发音
5. **完美兼容** - 与现有百度翻译 API 共存，保留原有功能

---

## 🚀 快速开始

### 1. 启动服务器
```bash
python manage.py runserver
```

### 2. 访问功能
- **首页**: http://127.0.0.1:8000/
- **DeepSeek 查询**: 点击首页 "DeepSeek Query" 卡片
- **AI 配置**: 点击首页 "AI Settings" 卡片

### 3. 使用流程
1. 登录系统
2. 进入 DeepSeek 查询页面
3. 输入英文单词（如 "apple"）
4. 点击"查询"按钮
5. 查看释义、音标、例句
6. 点击播放按钮试听发音
7. 点击"保存到单词本"按钮保存

---

## ⚙️ 配置说明

### API Key 配置
已在 `.env` 文件中配置：
```env
DEEPSEEK_API_KEY=sk-1af13fbd65ff4f5c8708259065e66445
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 温度参数建议
- **0.0** - 代码生成/数学解题（精确）
- **1.0** - 数据抽取/分析（平衡） ⭐ **推荐用于单词查询**
- **1.3** - 通用对话/翻译（灵活）
- **1.5** - 创意写作/诗歌（创意）

### System Prompt 优化
默认提示词：
```
你是英语词典助手。输入：英文单词。输出：JSON格式包含uk_phonetic(英音标)、us_phonetic(美音标)、meaning(中文释义)、example_sentences(2-3个例句数组，每个包含english和chinese字段)。目标用户：小学5年级。严格按照JSON格式输出，不要添加任何其他文字或markdown代码块标记。
```

可在 "AI Settings" 页面自定义修改。

---

## 📊 数据结构

### DeepSeek API 返回格式
```json
{
  "uk_phonetic": "/ˈæpl/",
  "us_phonetic": "/ˈæpl/",
  "meaning": "苹果",
  "example_sentences": [
    {
      "english": "I eat an apple every day.",
      "chinese": "我每天吃一个苹果。"
    }
  ]
}
```

### 保存到数据库的格式
- `item`: 单词名称（如 "apple"）
- `uk_phonetic`: 英式音标（如 "ˈæpl"）
- `us_phonetic`: 美式音标（如 "ˈæpl"）
- `content`: 释义和例句（文本格式）
- `src_tts`: Google TTS URL
- `inputDate` 和 `initDate`: 当前日期
- `category`: 默认保存到"单词"分类

---

## 🔄 与百度翻译的兼容性

### 保留原有功能
✅ 百度翻译 API 完全保留  
✅ 输入页面的"获取释义"功能正常  
✅ 数据结构完全兼容  

### 两套 API 对比
| 特性 | 百度翻译 | DeepSeek AI |
|------|---------|-------------|
| 音标 | ✅ | ✅ |
| 释义 | ✅ | ✅ |
| 例句 | ✅ | ✅ (更自然) |
| TTS | ✅ 百度服务 | ✅ Google TTS |
| 可配置性 | ❌ | ✅ (温度、prompt) |
| 个性化 | ❌ | ✅ |

### 切换方式
未来可在输入页面添加下拉框选择：
- 不获取释义
- 使用百度翻译
- 使用 DeepSeek AI

---

## 🎯 功能扩展建议

### 已实现 ✅
- [x] DeepSeek API 客户端
- [x] 配置管理界面
- [x] 独立查询页面
- [x] 数据保存功能
- [x] TTS 音频播放
- [x] 首页导航集成

### 可选增强 🔮
- [ ] 在输入页面集成 DeepSeek（替代或补充百度翻译）
- [ ] 批量查询功能
- [ ] 历史查询记录
- [ ] 自定义例句数量
- [ ] 支持更多 TTS 服务（Azure Speech）
- [ ] 错误重试机制（针对 429/503）
- [ ] 请求缓存（减少 API 调用）

---

## 🐛 故障排查

### 问题 1: 查询按钮禁用
**原因**: API Key 未配置  
**解决**: 检查 `.env` 文件中的 `DEEPSEEK_API_KEY`

### 问题 2: API 调用失败（404）
**原因**: `DEEPSEEK_BASE_URL` 配置错误  
**解决**: 确保设置为 `https://api.deepseek.com`（不要包含路径）

### 问题 3: TTS 播放失败
**原因**: Google TTS 可能被墙或浏览器限制  
**解决**: 
- 使用 VPN
- 替换为其他 TTS 服务
- 或设置 `src_tts` 为 `None`

### 问题 4: JSON 解析错误
**原因**: DeepSeek 返回了非标准 JSON（如带 markdown 包裹）  
**解决**: 已在 `parse_json_response()` 中处理，自动去除 markdown 标记

---

## 📝 测试验证

运行测试脚本：
```bash
python test_deepseek.py
```

预期输出：
```
✓ API Key 配置: 通过
✓ API 调用: 通过
✓ 数据兼容性: 通过

所有测试通过！DeepSeek API 已成功集成。
```

---

## 🔐 安全提示

1. **API Key 保护**: 
   - ✅ 已存储在 `.env` 文件中
   - ⚠️ 确保 `.env` 在 `.gitignore` 中
   - ⚠️ 不要提交 API Key 到 Git

2. **生产环境**:
   - 使用环境变量或密钥管理服务
   - 定期轮换 API Key
   - 监控 API 使用量和费用

---

## 📚 相关文件

### 核心模块
- `EAW/deepseek.py` - DeepSeek API 客户端
- `EAW/models.py` - DeepSeekConfig 数据模型
- `EAW/views.py` - 视图函数（配置/查询/保存）
- `EAW/forms.py` - DeepSeekConfigForm 表单
- `EAW/utils.py` - fetch_and_merge_deepseek 工具函数

### 模板文件
- `EAW/templates/deepseek_config.html` - 配置管理页面
- `EAW/templates/deepseek_query.html` - 查询页面
- `EAW/templates/home_logged_in.html` - 首页（含导航）

### 配置文件
- `.env` - 环境变量配置
- `EbbinghausAnywhere/settings.py` - Django 设置
- `EAW/urls.py` - URL 路由

### 测试文件
- `test_deepseek.py` - 集成测试脚本

---

## 🎉 完成状态

✅ **所有功能已实现并测试通过！**

开始使用 DeepSeek AI 增强你的单词学习体验吧！🚀
