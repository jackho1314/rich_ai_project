import unittest

from birthday_profile import compute_action_report, reduce_birth_energy


class BirthdayProfileTest(unittest.TestCase):
    def test_birth_energy_uses_month_and_day_only(self):
        self.assertEqual(reduce_birth_energy(12, 29), 5)
        self.assertEqual(reduce_birth_energy(3, 3), 6)

    def test_birth_energy_validates_calendar_day(self):
        with self.assertRaises(ValueError):
            reduce_birth_energy(2, 30)

    def test_action_report_reverse_scores_items(self):
        answers = {
            1: 4,
            2: 3,
            3: 3,
            4: 3,
            5: 3,
            6: 1,
            7: 2,
            8: 2,
            9: 2,
            10: 2,
        }
        report = compute_action_report(answers, 3)
        self.assertEqual(report["primary"], "O")
        self.assertEqual(report["combined_title"], "靈感型表達者")
        self.assertEqual(report["scores"]["O"], 100)
        self.assertNotIn("month", report)
        self.assertNotIn("day", report)

    def test_action_report_requires_all_ten_answers(self):
        with self.assertRaises(ValueError):
            compute_action_report({1: 4}, 1)


if __name__ == "__main__":
    unittest.main()
