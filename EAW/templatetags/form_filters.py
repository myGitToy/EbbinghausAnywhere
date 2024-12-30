# 在 app_name/templatetags/form_filters.py 中
from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """将指定的 class 添加到 HTML 输入字段中"""
    return value.as_widget(attrs={'class': arg})
