"""
百度翻译API可用性测试脚本
用于验证API密钥是否正确配置并可用
"""
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

def test_api_keys():
    """检查API密钥是否已配置"""
    print("=" * 60)
    print("步骤 1: 检查API密钥配置")
    print("=" * 60)
    
    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        print("❌ 错误: API密钥未配置")
        return False
    
    print(f"✅ BAIDU_API_KEY: {BAIDU_API_KEY}")
    print(f"✅ BAIDU_SECRET_KEY: {BAIDU_SECRET_KEY}")
    print(f"   密钥长度: API_KEY={len(BAIDU_API_KEY)}, SECRET_KEY={len(BAIDU_SECRET_KEY)}")
    return True

def test_access_token():
    """测试获取access_token"""
    print("\n" + "=" * 60)
    print("步骤 2: 获取 Access Token")
    print("=" * 60)
    
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    
    print(f"请求 URL: {url}")
    print(f"请求参数: grant_type=client_credentials")
    print(f"         client_id={BAIDU_API_KEY}")
    print(f"         client_secret={BAIDU_SECRET_KEY}")
    
    try:
        response = requests.post(url, params=params)
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                access_token = token_data["access_token"]
                print(f"\n✅ 成功获取 Access Token")
                print(f"   Token (前20字符): {access_token[:20]}...")
                return access_token
            else:
                print(f"\n❌ 响应中没有 access_token 字段")
                return None
        else:
            print(f"\n❌ 获取 access_token 失败")
            print(f"   可能的原因:")
            print(f"   1. API密钥不正确")
            print(f"   2. 密钥已过期")
            print(f"   3. 应用未启用或被冻结")
            return None
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return None

def test_translation(access_token, word="hello"):
    """测试翻译API"""
    print("\n" + "=" * 60)
    print(f"步骤 3: 测试翻译功能 (单词: {word})")
    print("=" * 60)
    
    url = f"https://aip.baidubce.com/rpc/2.0/mt/texttrans-with-dict/v1?access_token={access_token}"
    
    payload = json.dumps({
        "from": "en",
        "to": "zh",
        "q": word
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print(f"请求 URL: {url[:80]}...")
    print(f"请求数据: {payload}")
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 翻译请求成功")
            print("\n完整响应数据:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 解析并显示关键信息
            if 'result' in result and 'trans_result' in result['result']:
                trans_result = result['result']['trans_result'][0]
                
                print("\n" + "=" * 60)
                print("解析结果:")
                print("=" * 60)
                
                # 翻译文本
                if 'dst' in trans_result:
                    print(f"翻译结果: {trans_result['dst']}")
                
                # 字典内容
                if 'dict' in trans_result:
                    dict_content = trans_result['dict']
                    dict_data = json.loads(dict_content)
                    
                    # 提取音标
                    if 'word_result' in dict_data and 'simple_means' in dict_data['word_result']:
                        simple_means = dict_data['word_result']['simple_means']
                        
                        if 'symbols' in simple_means:
                            symbols = simple_means['symbols']
                            for symbol in symbols:
                                ph_en = symbol.get('ph_en', '')
                                ph_am = symbol.get('ph_am', '')
                                if ph_en:
                                    print(f"英式音标: /{ph_en}/")
                                if ph_am:
                                    print(f"美式音标: /{ph_am}/")
                        
                        # 提取释义
                        if 'symbols' in simple_means:
                            print("\n词性和释义:")
                            for symbol in simple_means['symbols']:
                                if 'parts' in symbol:
                                    for part in symbol['parts']:
                                        part_name = part.get('part', '')
                                        means = part.get('means', [])
                                        if means:
                                            means_str = '; '.join([m.get('mean', m) if isinstance(m, dict) else m for m in means])
                                            print(f"  {part_name}: {means_str}")
                
                # TTS音频链接
                if 'src_tts' in trans_result:
                    print(f"\nTTS音频: {trans_result['src_tts']}")
                
                return True
            else:
                print("\n⚠️ 响应中缺少翻译结果")
                return False
        else:
            print(f"\n❌ 翻译请求失败")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("百度翻译API可用性测试")
    print("=" * 60)
    
    # 步骤1: 检查密钥
    if not test_api_keys():
        print("\n❌ 测试终止: 请先配置API密钥")
        return
    
    # 步骤2: 获取access_token
    access_token = test_access_token()
    if not access_token:
        print("\n❌ 测试终止: 无法获取access_token")
        print("\n建议:")
        print("1. 检查API密钥是否正确")
        print("2. 登录百度智能云控制台验证应用状态")
        print("3. 确认应用已开通'文本翻译-词典版'服务")
        return
    
    # 步骤3: 测试翻译
    success = test_translation(access_token, "hello")
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过! 百度翻译API可正常使用")
    else:
        print("❌ 测试失败，请检查上述错误信息")
    print("=" * 60)

if __name__ == "__main__":
    main()
