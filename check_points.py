import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')

import django
django.setup()

from EAW.models import User, UserPoints
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
if user:
    points, created = UserPoints.objects.get_or_create(user=user)
    print('User: {}'.format(user.username))
    print('Current points: {}'.format(points.current_points))
    print('Total earned: {}'.format(points.total_earned))
    print('Total spent: {}'.format(points.total_spent))
    print('Is spent None: {}'.format(points.total_spent is None))
    print('Was just created: {}'.format(created))
else:
    print('No users found')

