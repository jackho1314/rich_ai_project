import unittest

from birthday_profile import (
    build_life_path_report,
    calculate_life_path,
    compute_humanity_report,
)


def answers_with_counts(*, tiger: int, dolphin: int, penguin: int, bee: int):
    values = [1] * tiger + [2] * dolphin + [3] * penguin + [4] * bee
    return {index: value for index, value in enumerate(values, start=1)}


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

    def test_seven_is_standard_animal_type(self):
        report = compute_humanity_report(
            answers_with_counts(tiger=7, dolphin=5, penguin=4, bee=4),
            3,
        )
        self.assertEqual(report["animal_title"], "老虎")
        self.assertEqual(report["combined_title"], "3號表達者 × 老虎")
        self.assertEqual(report["animal_intensity"], "standard")

    def test_above_seven_is_big_animal_type(self):
        report = compute_humanity_report(
            answers_with_counts(tiger=4, dolphin=4, penguin=4, bee=8),
            7,
        )
        self.assertEqual(report["animal_title"], "大蜜蜂")
        self.assertEqual(report["combined_title"], "7號洞察者 × 大蜜蜂")
        self.assertEqual(report["animal_intensity"], "big")

    def test_top_tie_is_visible_as_two_primary_types(self):
        report = compute_humanity_report(
            answers_with_counts(tiger=7, dolphin=7, penguin=3, bee=3),
            2,
        )
        self.assertTrue(report["is_mixed"])
        self.assertEqual(report["animal_title"], "老虎 × 海豚")
        self.assertEqual(report["primary"], "tiger")
        self.assertEqual(report["secondary"], "dolphin")

    def test_balanced_scores_are_octopus(self):
        report = compute_humanity_report(
            answers_with_counts(tiger=5, dolphin=5, penguin=5, bee=5),
            9,
        )
        self.assertEqual(report["animal_title"], "八爪")
        self.assertEqual(report["primary"], "octopus")
        self.assertEqual(report["animal_intensity"], "balanced")

    def test_report_requires_all_twenty_answers(self):
        with self.assertRaises(ValueError):
            compute_humanity_report({1: 1}, 1)

    def test_report_never_contains_raw_birth_date(self):
        report = compute_humanity_report(
            answers_with_counts(tiger=8, dolphin=4, penguin=4, bee=4),
            6,
        )
        for forbidden in ("birth_year", "birth_month", "birth_day", "year", "month", "day"):
            self.assertNotIn(forbidden, report)


if __name__ == "__main__":
    unittest.main()
