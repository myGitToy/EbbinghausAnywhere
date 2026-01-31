"""简化版百度API测试"""
import requests
import json
import environ
from pathlib import Path

# 读取环境变量
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent
environ.Env.read_env(BASE_DIR / '.env')

BAIDU_API_KEY = env('BAIDU_API_KEY', default=None)
BAIDU_SECRET_KEY = env('BAIDU_SECRET_KEY', default=None)

print("步骤1: 检查密钥")
print(f"API_KEY: {BAIDU_API_KEY}")
print(f"SECRET_KEY: {BAIDU_SECRET_KEY}")
print()

print("步骤2: 获取 access_token")
url = "https://aip.baidubce.com/oauth/2.0/token"
params = {
    "grant_type": "client_credentials",
    "client_id": BAIDU_API_KEY,
    "client_secret": BAIDU_SECRET_KEY
}

try:
    print(f"请求: {url}")
    response = requests.post(url, params=params, timeout=10)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            token = data["access_token"]
            print(f"✅ Token获取成功: {token[:30]}...")
            print()
            
            print("步骤3: 测试翻译")
            trans_url = f"https://aip.baidubce.com/rpc/2.0/mt/texttrans-with-dict/v1?access_token={token}"
            payload = json.dumps({"from": "en", "to": "zh", "q": "hello"})
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            
            trans_response = requests.post(trans_url, headers=headers, data=payload, timeout=10)
            print(f"状态码: {trans_response.status_code}")
            
            if trans_response.status_code == 200:
                result = trans_response.json()
                print("✅ 翻译成功")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"❌ 翻译失败: {trans_response.text}")
        else:
            print(f"❌ 响应中无access_token")
            print(f"错误: {data}")
    else:
        print(f"❌ 获取token失败")
        error_data = response.json() if response.text else {}
        print(f"错误信息: {error_data}")
        
except requests.exceptions.Timeout:
    print("❌ 请求超时，请检查网络连接")
except Exception as e:
    print(f"❌ 异常: {e}")
