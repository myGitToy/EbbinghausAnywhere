#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EbbinghausAnywhere.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    # 在 Windows 上设置控制台为 UTF-8 模式
    if sys.platform == 'win32':
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'UTF-8')
        except:
            pass  # 如果设置失败就忽略
    main()
