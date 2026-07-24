import unittest

from birthday_profile import (
    build_life_path_report,
    calculate_life_path,
    compute_humanity_report,
)


def balanced_answers():
    return {index: 3 for index in range(1, 21)}


def answers_for_tiger():
    answers = balanced_answers()
    answers.update(
        {
            1: 5,
            6: 1,
            11: 5,
            16: 1,
            2: 1,
            7: 5,
            12: 1,
            17: 5,
            3: 5,
            8: 1,
            13: 5,
            18: 1,
        }
    )
    return answers


class HumanityProfileTest(unittest.TestCase):
    def test_life_path_uses_full_birth_date(self):
        self.assertEqual(calculate_life_path(1990, 12, 29), 6)
        self.assertEqual(calculate_life_path(1991, 12, 29), 7)

    def test_life_path_validates_calendar_date(self):
        with self.assertRaises(ValueError):
            calculate_life_path(2023, 2, 29)

    def test_full_life_path_report_cross_reads_the_birth_date(self):
        report = build_life_path_report(1990, 12, 29, current_year=2026)

        self.assertEqual(report["life_path"], 6)
        self.assertEqual(report["birthday_number"], 2)
        self.assertEqual(report["attitude_number"], 5)
        self.assertEqual(report["month_number"], 3)
        self.assertEqual(report["generation_number"], 1)
        self.assertEqual(report["personal_year"], 6)
        self.assertEqual(report["repeated_numbers"][0]["number"], 9)
        self.assertEqual(report["repeated_numbers"][0]["count"], 3)
        self.assertIn(3, report["missing_numbers"])

    def test_full_life_path_report_does_not_return_raw_birth_date(self):
        report = build_life_path_report(1990, 12, 29, current_year=2026)

        for forbidden in (
            "birth_year",
            "birth_month",
            "birth_day",
            "year",
            "month",
            "day",
        ):
            self.assertNotIn(forbidden, report)

    def test_reverse_keyed_items_produce_five_trait_scores(self):
        report = compute_humanity_report(
            answers_for_tiger(),
            3,
        )
        self.assertEqual(
            report["trait_scores"],
            {
                "外向互動": 100,
                "同理合作": 0,
                "規劃執行": 100,
                "情緒穩定": 50,
                "開放探索": 50,
            },
        )
        self.assertEqual(report["animal_title"], "老虎 × 海豚")
        self.assertEqual(report["combined_title"], "3號表達者｜老虎 × 海豚")
        self.assertEqual(report["animal_intensity"], "primary")

    def test_close_top_scores_are_visible_as_dual_core(self):
        answers = answers_for_tiger()
        answers.update({2: 5, 7: 1, 12: 5, 17: 1})
        report = compute_humanity_report(
            answers,
            2,
        )
        self.assertTrue(report["is_mixed"])
        self.assertEqual(report["animal_title"], "老虎 × 海豚")
        self.assertEqual(report["primary"], "tiger")
        self.assertEqual(report["secondary"], "dolphin")
        self.assertEqual(report["animal_balance_label"], "雙核心風格")

    def test_balanced_scores_are_octopus(self):
        report = compute_humanity_report(
            balanced_answers(),
            9,
        )
        self.assertEqual(report["animal_title"], "八爪平衡型")
        self.assertEqual(report["primary"], "octopus")
        self.assertEqual(report["animal_intensity"], "balanced")
        self.assertEqual(
            report["animal_scores"],
            {"老虎": 50, "海豚": 50, "企鵝": 50, "蜜蜂": 50},
        )

    def test_report_requires_all_twenty_answers(self):
        with self.assertRaises(ValueError):
            compute_humanity_report({1: 1}, 1)

    def test_report_never_contains_raw_birth_date(self):
        report = compute_humanity_report(
            answers_for_tiger(),
            6,
        )
        for forbidden in ("birth_year", "birth_month", "birth_day", "year", "month", "day"):
            self.assertNotIn(forbidden, report)


if __name__ == "__main__":
    unittest.main()
