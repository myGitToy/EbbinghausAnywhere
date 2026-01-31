import requests
import json
import os
from pathlib import Path

# 手动读取.env
env_file = Path(__file__).parent / '.env'
env_vars = {}
with open(env_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value

BAIDU_API_KEY = env_vars.get('BAIDU_API_KEY', '').strip()
BAIDU_SECRET_KEY = env_vars.get('BAIDU_SECRET_KEY', '').strip()

print("="*60)
print("百度翻译API测试")
print("="*60)
print(f"API Key: {BAIDU_API_KEY}")
print(f"Secret Key: {BAIDU_SECRET_KEY}")
print()

# 测试获取token
print("正在获取 access_token...")
url = "https://aip.baidubce.com/oauth/2.0/token"
params = {
    "grant_type": "client_credentials",
    "client_id": BAIDU_API_KEY,
    "client_secret": BAIDU_SECRET_KEY
}

try:
    response = requests.post(url, params=params, timeout=5)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            token = data["access_token"]
            print(f"✅ Token获取成功!")
            print(f"Token (前20字符): {token[:20]}...")
            
            # 测试翻译
            print("\n正在测试翻译 (hello)...")
            trans_url = f"https://aip.baidubce.com/rpc/2.0/mt/texttrans-with-dict/v1?access_token={token}"
            payload = json.dumps({"from": "en", "to": "zh", "q": "hello"})
            headers = {'Content-Type': 'application/json'}
            
            trans_response = requests.post(trans_url, headers=headers, data=payload, timeout=5)
            print(f"翻译状态码: {trans_response.status_code}")
            
            if trans_response.status_code == 200:
                result = trans_response.json()
                print("\n✅ 翻译成功!")
                
                if 'result' in result and 'trans_result' in result['result']:
                    trans = result['result']['trans_result'][0]
                    print(f"原文: {trans.get('src')}")
                    print(f"译文: {trans.get('dst')}")
                    
                    if 'dict' in trans:
                        dict_data = json.loads(trans['dict'])
                        if 'word_result' in dict_data and 'simple_means' in dict_data['word_result']:
                            simple_means = dict_data['word_result']['simple_means']
                            if 'symbols' in simple_means:
                                for symbol in simple_means['symbols']:
                                    ph_en = symbol.get('ph_en', '')
                                    ph_am = symbol.get('ph_am', '')
                                    if ph_en:
                                        print(f"英式音标: /{ph_en}/")
                                    if ph_am:
                                        print(f"美式音标: /{ph_am}/")
                print("\n✅ 所有测试通过!")
            else:
                print(f"❌ 翻译失败: {trans_response.text}")
        else:
            print(f"❌ 响应中无token: {data}")
    else:
        print(f"❌ 获取token失败: {response.text}")
        
except requests.Timeout:
    print("❌ 请求超时")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
