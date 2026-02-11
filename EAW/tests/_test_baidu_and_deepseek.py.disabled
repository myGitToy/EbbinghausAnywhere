from django.test import TestCase
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

class ExternalApiKeysTest(TestCase):
    def setUp(self):
        if (BASE_DIR / '.env').exists():
            environ.Env.read_env(BASE_DIR / '.env')

    def test_baidu_keys_present(self):
        api = env('BAIDU_API_KEY', default=None)
        secret = env('BAIDU_SECRET_KEY', default=None)
        if not api or not secret:
            self.skipTest('BAIDU keys not configured; skipping network test')
        # If present, at least assert they are non-empty strings
        self.assertTrue(isinstance(api, str) and len(api) > 0)
        self.assertTrue(isinstance(secret, str) and len(secret) > 0)

    def test_deepseek_key_present(self):
        key = env('DEEPSEEK_API_KEY', default=None)
        if not key:
            self.skipTest('DEEPSEEK key not configured; skipping network test')
        self.assertTrue(isinstance(key, str) and len(key) > 0)
