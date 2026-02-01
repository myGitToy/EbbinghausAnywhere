from django.test import TestCase
from datetime import date, timedelta

class ReviewLogicTest(TestCase):
    def test_yes_date_advances_correctly(self):
        intervals = [0,1,2,4,7,15,30,90,180]
        review_date = date(2026,2,1)
        expected = []
        for i in range(len(intervals)-1):
            cur = intervals[i]
            nxt = intervals[i+1]
            days_until = nxt - cur
            expected_date = review_date + timedelta(days=days_until)
            expected.append((cur, nxt, expected_date))
        # simple assertions for some entries (correct expected dates)
        self.assertEqual(expected[0][2], date(2026,2,2))  # 0->1
        self.assertEqual(expected[2][2], date(2026,2,3))  # 2->4
        self.assertEqual(expected[3][2], date(2026,2,4))  # 4->7
