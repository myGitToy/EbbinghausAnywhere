from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from EAW.models import Item, Category, Proficiency

class YesNoBehaviorTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user, created = User.objects.get_or_create(username='auto_test_user')
        if created:
            self.user.set_password('pass')
            self.user.save()
        self.client = Client()
        self.client.login(username=self.user.username, password='pass')
        self.cat, _ = Category.objects.get_or_create(user=self.user, name='自动测试')
        self.today = date.today()

    def pretty(self, item):
        return {
            'id': item.id,
            'current_interval': item.current_interval,
            'next_review_date': item.next_review_date.isoformat() if item.next_review_date else None,
            'proficiency': item.get_proficiency_display(),
            'needs_extra_review': item.needs_extra_review,
            'extra_review_since': item.extra_review_since.isoformat() if item.extra_review_since else None,
            'unfamiliar_history': item.unfamiliar_history or []
        }

    def test_yes_on_regular_advances_interval(self):
        it = Item.objects.create(user=self.user, category=self.cat, item='auto_yes', content='t', inputDate=self.today, initDate=self.today, current_interval=0, next_review_date=self.today, proficiency=Proficiency.UNFAMILIAR, unfamiliar_history=[])
        resp = self.client.post('/review-feedback/yes/', data={'id': it.id, 'date': self.today.isoformat()}, content_type='application/json')
        it.refresh_from_db()
        self.assertEqual(it.current_interval, 1)
        self.assertEqual(it.next_review_date, self.today + timedelta(days=1))
        self.assertEqual(it.proficiency, Proficiency.MASTERED)

    def test_no_on_regular_sets_extra_review(self):
        it = Item.objects.create(user=self.user, category=self.cat, item='auto_no_reg', content='t', inputDate=self.today, initDate=self.today, current_interval=1, next_review_date=self.today, proficiency=Proficiency.MASTERED, unfamiliar_history=[])
        resp = self.client.post('/review-feedback/no/', data={'id': it.id, 'date': self.today.isoformat()}, content_type='application/json')
        it.refresh_from_db()
        self.assertEqual(it.proficiency, Proficiency.UNFAMILIAR)
        self.assertTrue(it.needs_extra_review)
        self.assertEqual(it.extra_review_since, self.today + timedelta(days=1))
        self.assertGreaterEqual(len(it.unfamiliar_history or []), 1)

    def test_no_on_extra_keeps_next_date_and_records_extra(self):
        future = self.today + timedelta(days=10)
        it = Item.objects.create(user=self.user, category=self.cat, item='auto_no_extra', content='t', inputDate=self.today, initDate=self.today, current_interval=2, next_review_date=future, proficiency=Proficiency.MASTERED, unfamiliar_history=[], needs_extra_review=True, extra_review_since=self.today)
        resp = self.client.post('/review-feedback/no/', data={'id': it.id, 'date': self.today.isoformat()}, content_type='application/json')
        it.refresh_from_db()
        self.assertEqual(it.proficiency, Proficiency.UNFAMILIAR)
        self.assertEqual(it.next_review_date, future)
        self.assertGreaterEqual(len(it.unfamiliar_history or []), 1)
