import os
from django.test import TestCase
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

class ConfigEnvTest(TestCase):
    def test_env_file_exists(self):
        self.assertTrue((BASE_DIR / '.env').exists())

    def test_baidu_keys_present_or_skip(self):
        # If .env exists, read and make a best-effort assertion
        if (BASE_DIR / '.env').exists():
            environ.Env.read_env(BASE_DIR / '.env')
            api = env('BAIDU_API_KEY', default=None)
            secret = env('BAIDU_SECRET_KEY', default=None)
            # Not mandatory for CI; just assert presence if intended
            # If missing, test will fail to remind configuration
            self.assertIsNotNone(api)
            self.assertIsNotNone(secret)
