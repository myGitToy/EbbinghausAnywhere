# 在Django项目中测试百度API
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from EAW.translate import baidu_translate, BAIDU_API_KEY, BAIDU_SECRET_KEY

print("="*60)
print("百度翻译API测试 (Django环境)")
print("="*60)
print(f"API Key: {BAIDU_API_KEY}")
print(f"Secret Key: {BAIDU_SECRET_KEY}")
print()

print("测试翻译单词: hello")
result = baidu_translate("hello")

if result:
    print("\n✅ 翻译成功!")
    print(f"音标: {result.get('phonetic', [])}")
    print(f"释义: {result.get('parts_and_means', [])}")
    print(f"TTS: {result.get('src_tts', 'None')}")
else:
    print("\n❌ 翻译失败，请查看上方的错误信息")

print("\n" + "="*60)
