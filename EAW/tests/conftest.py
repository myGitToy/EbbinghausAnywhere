import os
import django
from django.conf import settings


def pytest_configure(config):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EbbinghausAnywhere.settings")
    django.setup()
