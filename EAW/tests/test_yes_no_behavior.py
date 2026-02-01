#!/usr/bin/env python
import os
import django
from datetime import date, timedelta
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EbbinghausAnywhere.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from EAW.models import Item, Category, Proficiency

INTERVALS = [0,1,2,4,7,15,30,90,180]


def create_user(username='testuser', password='testpass'):
    User = get_user_model()
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()
    return user, password


def mkcat(user):
    cat, _ = Category.objects.get_or_create(user=user, name='测试')
    return cat


def pretty(item):
    return {
        'id': item.id,
        'current_interval': item.current_interval,
        'next_review_date': item.next_review_date.isoformat() if item.next_review_date else None,
        'proficiency': item.get_proficiency_display(),
        'needs_extra_review': item.needs_extra_review,
        'extra_review_since': item.extra_review_since.isoformat() if item.extra_review_since else None,
        'unfamiliar_history': item.unfamiliar_history or []
    }


def run_test():
    user, pwd = create_user()
    client = Client()
    logged = client.login(username=user.username, password=pwd)
    if not logged:
        raise RuntimeError('login failed')

    cat = mkcat(user)
    today = date.today()

    results = []

    # Test 1: Regular YES (Day0 -> Day1)
    it1 = Item.objects.create(user=user, category=cat, item='t_yes', content='t', inputDate=today, initDate=today, current_interval=0, next_review_date=today, proficiency=Proficiency.UNFAMILIAR, unfamiliar_history=[])
    before = pretty(it1)
    resp = client.post('/review-feedback/yes/', data=json.dumps({'id': it1.id, 'date': today.isoformat()}), content_type='application/json')
    it1.refresh_from_db()
    after = pretty(it1)
    expected_next = (today + timedelta(days=1)).isoformat()
    ok1 = (after['current_interval'] == 1 and after['next_review_date'] == expected_next and after['proficiency'] == 'Mastered')
    results.append(('YES_regular', before, json.loads(resp.content), after, ok1))

    # Test 2: Regular NO (Day1 stays Day1, extra_review set)
    it2 = Item.objects.create(user=user, category=cat, item='t_no_reg', content='t', inputDate=today, initDate=today, current_interval=1, next_review_date=today, proficiency=Proficiency.MASTERED, unfamiliar_history=[])
    before = pretty(it2)
    resp = client.post('/review-feedback/no/', data=json.dumps({'id': it2.id, 'date': today.isoformat()}), content_type='application/json')
    it2.refresh_from_db()
    after = pretty(it2)
    ok2 = (after['proficiency'] == 'Unfamiliar' and after['needs_extra_review'] is True and after['extra_review_since'] == (today + timedelta(days=1)).isoformat() and len(after['unfamiliar_history']) >= 1)
    results.append(('NO_regular', before, json.loads(resp.content), after, ok2))

    # Test 3: Extra-review NO (next_review_date in future, needs_extra_review True)
    future = today + timedelta(days=10)
    it3 = Item.objects.create(user=user, category=cat, item='t_no_extra', content='t', inputDate=today, initDate=today, current_interval=2, next_review_date=future, proficiency=Proficiency.MASTERED, unfamiliar_history=[], needs_extra_review=True, extra_review_since=today)
    before = pretty(it3)
    resp = client.post('/review-feedback/no/', data=json.dumps({'id': it3.id, 'date': today.isoformat()}), content_type='application/json')
    it3.refresh_from_db()
    after = pretty(it3)
    ok3 = (after['proficiency'] == 'Unfamiliar' and after['next_review_date'] == future.isoformat() and len(after['unfamiliar_history']) >= 1)
    results.append(('NO_extra', before, json.loads(resp.content), after, ok3))

    # Print results succinctly
    for name, before, respjson, after, ok in results:
        print('---', name, 'OK' if ok else 'FAIL')
        print('before:', before)
        print('response:', respjson)
        print('after :', after)

    # Return exit code
    all_ok = all(r[-1] for r in results)
    print('\nSummary: all_ok=', all_ok)
    return 0 if all_ok else 2

if __name__ == '__main__':
    exit(run_test())
