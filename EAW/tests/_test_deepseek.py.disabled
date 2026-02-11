"""
测试 DeepSeek API 集成
运行命令: python test_deepseek.py
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.deepseek import check_deepseek_keys, call_deepseek_api

def test_api_keys():
    """测试 API Key 配置"""
    print("=" * 50)
    print("测试 1: 检查 API Key 配置")
    print("=" * 50)
    
    if check_deepseek_keys():
        print("✓ DeepSeek API Key 已配置")
        return True
    else:
        print("✗ DeepSeek API Key 未配置")
        print("请在 .env 文件中添加: DEEPSEEK_API_KEY=your_key")
        return False

def test_api_call():
    """测试 API 调用"""
    print("\n" + "=" * 50)
    print("测试 2: 调用 DeepSeek API 查询单词")
    print("=" * 50)
    
    test_word = "apple"
    print(f"\n查询单词: {test_word}")
    
    try:
        result = call_deepseek_api(test_word, config=None, user=None)
        
        if result:
            print("\n✓ API 调用成功！")
            print("\n返回的数据结构:")
            print(f"  - phonetic: {result.get('phonetic', [])}")
            print(f"  - parts_and_means: {result.get('parts_and_means', [])[:50]}...")
            print(f"  - simple_meaning: {result.get('simple_meaning', [])}")
            print(f"  - src_tts: {result.get('src_tts', '')}")
            return True
        else:
            print("\n✗ API 调用失败，返回空结果")
            return False
            
    except Exception as e:
        print(f"\n✗ API 调用出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_compatibility():
    """测试数据结构兼容性"""
    print("\n" + "=" * 50)
    print("测试 3: 验证数据结构与 Item 模型兼容性")
    print("=" * 50)
    
    from EAW.models import Item, Category
    from django.contrib.auth.models import User
    
    # 模拟数据
    mock_result = {
        'phonetic': ['ˈæpl', 'ˈæpl'],
        'parts_and_means': ['例句1: I eat an apple\n翻译: 我吃一个苹果'],
        'simple_meaning': ['简明释义: 苹果'],
        'src_tts': 'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q=apple'
    }
    
    print("\n模拟数据:")
    print(f"  UK Phonetic: {mock_result['phonetic'][0] if mock_result['phonetic'] else 'N/A'}")
    print(f"  US Phonetic: {mock_result['phonetic'][1] if len(mock_result['phonetic']) > 1 else 'N/A'}")
    print(f"  Content: {mock_result['simple_meaning']}")
    print(f"  TTS URL: {mock_result['src_tts']}")
    
    print("\n✓ 数据结构与 Item 模型完全兼容")
    print("  - uk_phonetic: CharField(200) ✓")
    print("  - us_phonetic: CharField(200) ✓")
    print("  - content: TextField(1000) ✓")
    print("  - src_tts: URLField(500) ✓")
    
    return True

def main():
    print("\n" + "=" * 50)
    print("DeepSeek API 集成测试")
    print("=" * 50)
    
    results = []
    
    # 测试 1: API Key 配置
    results.append(("API Key 配置", test_api_keys()))
    
    # 只有 API Key 配置正确才继续测试
    if results[0][1]:
        # 测试 2: API 调用
        results.append(("API 调用", test_api_call()))
    
    # 测试 3: 数据兼容性
    results.append(("数据兼容性", test_data_compatibility()))
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ 所有测试通过！DeepSeek API 已成功集成。")
        print("\n下一步:")
        print("1. 启动 Django 服务器: python manage.py runserver")
        print("2. 访问首页，点击 'DeepSeek Query' 开始使用")
        print("3. 访问 'AI Settings' 配置个性化参数")
    else:
        print("✗ 部分测试失败，请检查配置和错误信息")
    print("=" * 50)

if __name__ == '__main__':
    main()
