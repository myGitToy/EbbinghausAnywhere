"""本地测试 - 仅检查配置"""
import environ
from pathlib import Path

print("=" * 60)
print("本地配置检查")
print("=" * 60)

# 读取环境变量
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent
print(f"BASE_DIR: {BASE_DIR}")
print(f".env文件路径: {BASE_DIR / '.env'}")
print(f".env文件存在: {(BASE_DIR / '.env').exists()}")
print()

environ.Env.read_env(BASE_DIR / '.env')

BAIDU_API_KEY = env('BAIDU_API_KEY', default=None)
BAIDU_SECRET_KEY = env('BAIDU_SECRET_KEY', default=None)

print("读取的环境变量:")
print(f"  BAIDU_API_KEY: '{BAIDU_API_KEY}'")
print(f"  长度: {len(BAIDU_API_KEY) if BAIDU_API_KEY else 0}")
print(f"  BAIDU_SECRET_KEY: '{BAIDU_SECRET_KEY}'")
print(f"  长度: {len(BAIDU_SECRET_KEY) if BAIDU_SECRET_KEY else 0}")
print()

if BAIDU_API_KEY and BAIDU_SECRET_KEY:
    print("✅ 密钥配置正常")
    
    # 检查密钥格式
    import re
    if re.match(r'^[a-zA-Z0-9_]+$', BAIDU_API_KEY):
        print("✅ API_KEY 格式正常（字母数字下划线）")
    else:
        print("⚠️ API_KEY 包含特殊字符")
    
    if re.match(r'^[a-zA-Z0-9_]+$', BAIDU_SECRET_KEY):
        print("✅ SECRET_KEY 格式正常（字母数字下划线）")
    else:
        print("⚠️ SECRET_KEY 包含特殊字符")
else:
    print("❌ 密钥未配置")

print()
print("=" * 60)
print("配置检查完成")
print("=" * 60)
