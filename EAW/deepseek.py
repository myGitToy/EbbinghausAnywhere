# deepseek.py
"""
DeepSeek API 客户端模块
提供与 DeepSeek API 交互的功能，并将返回结果转换为与百度翻译兼容的格式
"""

import json
import re
import environ
from pathlib import Path
from openai import OpenAI
from django.conf import settings

env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')

# 获取 DeepSeek API 配置
DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default=None)
DEEPSEEK_BASE_URL = env('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')


def check_deepseek_keys():
    """
    检查是否配置了 DeepSeek API 密钥
    :return: True 如果配置了密钥，否则返回 False
    """
    return bool(DEEPSEEK_API_KEY)


def call_deepseek_api(word, config=None, user=None):
    """
    调用 DeepSeek API 获取单词释义
    
    :param word: 要查询的单词
    :param config: DeepSeekConfig 实例（可选）
    :param user: 用户实例（可选，用于获取默认配置）
    :return: 解析后的 JSON 字典，或失败时返回空字典 {}
    """
    if not DEEPSEEK_API_KEY:
        print("DeepSeek API 密钥未配置")
        return {}
    
    # 如果没有提供 config，尝试从 user 获取或使用默认值
    if config is None and user:
        from .models import DeepSeekConfig
        try:
            config = DeepSeekConfig.objects.get(user=user)
        except DeepSeekConfig.DoesNotExist:
            # 使用默认配置
            config = None
    
    # 设置默认参数
    model = config.model if config else 'deepseek-chat'
    temperature = config.temperature if config else 1.0
    system_prompt = config.system_prompt if config else (
        '你是英语词典助手。输入：英文单词。输出：JSON格式包含uk_phonetic(英音标)、'
        'us_phonetic(美音标)、meaning(中文释义)、example_sentences(2-3个例句数组，'
        '每个包含english和chinese字段)。目标用户：小学5年级。'
        '严格按照JSON格式输出，不要添加任何其他文字或markdown代码块标记。'
    )
    
    try:
        # 初始化 OpenAI 客户端，使用 DeepSeek 的 base_url
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        
        print(f"=== 调用 DeepSeek API ===")
        print(f"Word: {word}")
        print(f"Model: {model}")
        print(f"Temperature: {temperature}")
        
        # 调用 API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": word}
            ],
            temperature=temperature,
            stream=False
        )
        
        # 获取响应内容
        content = response.choices[0].message.content
        print(f"=== DeepSeek API 响应 ===")
        print(content)
        
        # 解析 JSON 响应
        json_data = parse_json_response(content)
        
        if not json_data:
            print("解析 JSON 响应失败")
            return {}
        
        # 转换为与百度翻译兼容的格式
        result = parse_deepseek_to_baidu_format(json_data, word)
        return result
        
    except Exception as e:
        print(f"DeepSeek API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def parse_json_response(response_text):
    """
    解析 DeepSeek 返回的 JSON 响应，处理可能的 markdown 代码块包裹
    
    :param response_text: API 返回的原始文本
    :return: 解析后的 Python 字典，或失败时返回 None
    """
    try:
        # 去除前后空白字符
        response_text = response_text.strip()
        
        # 去除可能的 markdown 代码块标记
        if response_text.startswith('```'):
            # 去除开头的 ```json 或 ```
            response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
            # 去除结尾的 ```
            response_text = re.sub(r'\n?```\s*$', '', response_text)
            response_text = response_text.strip()
        
        # 解析 JSON
        json_data = json.loads(response_text)
        return json_data
        
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"原始响应: {response_text}")
        return None


def parse_deepseek_to_baidu_format(json_data, word):
    """
    将 DeepSeek 返回的 JSON 转换为与百度翻译兼容的格式
    
    DeepSeek 格式:
    {
        "uk_phonetic": "/ˈæpl/",
        "us_phonetic": "/ˈæpl/",
        "meaning": "苹果",
        "example_sentences": [
            {"english": "...", "chinese": "..."}
        ]
    }
    
    百度翻译格式:
    {
        "phonetic": ["英式音标", "美式音标"],
        "parts_and_means": ["词性: n.\\n释义: xxx"],
        "simple_meaning": ["简明释义: xxx"],
        "src_tts": "https://..."
    }
    
    :param json_data: DeepSeek 返回的 JSON 字典
    :param word: 查询的单词（用于生成 TTS URL）
    :return: 百度翻译格式的字典
    """
    try:
        result = {
            "phonetic": [],
            "parts_and_means": [],
            "simple_meaning": [],
            "src_tts": None
        }
        
        # 提取音标
        uk_phonetic = json_data.get("uk_phonetic", "")
        us_phonetic = json_data.get("us_phonetic", "")
        
        # 标准化音标格式（去除可能的包裹符号）
        if uk_phonetic:
            uk_phonetic = uk_phonetic.strip().strip('[]/')
            result["phonetic"].append(uk_phonetic)
        
        if us_phonetic:
            us_phonetic = us_phonetic.strip().strip('[]/')
            result["phonetic"].append(us_phonetic)
        
        # 提取释义
        meaning = json_data.get("meaning", "")
        if meaning:
            result["simple_meaning"].append(f"简明释义: {meaning}")
        
        # 提取例句
        example_sentences = json_data.get("example_sentences", [])
        if example_sentences:
            examples_text = []
            for idx, example in enumerate(example_sentences, 1):
                english = example.get("english", "")
                chinese = example.get("chinese", "")
                if english and chinese:
                    examples_text.append(f"例句{idx}: {english}")
                    examples_text.append(f"翻译: {chinese}")
            
            if examples_text:
                result["parts_and_means"].append("\n".join(examples_text))
        
        # 生成 Google TTS URL
        # 注意：Google TTS 可能在国内无法访问，这里仅作为示例
        # 实际使用时可能需要替换为其他 TTS 服务
        result["src_tts"] = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}"
        
        return result
        
    except Exception as e:
        print(f"转换格式失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "phonetic": [],
            "parts_and_means": [],
            "simple_meaning": [],
            "src_tts": None
        }


def deepseek_translate(word, user=None):
    """
    封装的翻译函数，与 baidu_translate 接口保持一致
    
    :param word: 要翻译的单词
    :param user: 用户实例（可选）
    :return: 百度翻译格式的字典
    """
    from .models import DeepSeekConfig
    
    # 获取用户配置
    config = None
    if user:
        try:
            config = DeepSeekConfig.objects.get(user=user, is_active=True)
        except DeepSeekConfig.DoesNotExist:
            pass
    
    return call_deepseek_api(word, config=config, user=user)
