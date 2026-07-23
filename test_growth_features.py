import unittest
from pathlib import Path

from growth_features import (
    AcquisitionContext,
    EVENT_COLUMNS,
    build_campaign_share_pack,
    build_event_row,
    build_partner_share_pack,
    build_share_url,
    entry_copy,
)


class GrowthFeaturesTest(unittest.TestCase):
    def test_context_normalizes_unknown_values(self):
        context = AcquisitionContext.from_values(
            ref_input=" Alice ",
            source="IG",
            campaign=" launch ",
            entry="unknown",
            forced_quiz="other",
        )
        self.assertEqual(context.ref_input, "alice")
        self.assertEqual(context.source, "ig")
        self.assertEqual(context.entry, "friend")
        self.assertEqual(context.forced_quiz, "")

    def test_entry_copy_is_distinct_for_each_audience(self):
        copies = []
        for entry in ("friend", "cold", "social"):
            context = AcquisitionContext.from_values(
                ref_input="master",
                source="line",
                campaign="organic",
                entry=entry,
                forced_quiz="",
            )
            copies.append(entry_copy(context, "Rich")["title"])
        self.assertEqual(len(set(copies)), 3)

    def test_share_url_preserves_tracking_context(self):
        context = AcquisitionContext.from_values(
            ref_input="ting",
            source="line",
            campaign="income01",
            entry="friend",
            forced_quiz="wealth",
        )
        url = build_share_url("https://example.com/", context, "wealth")
        self.assertIn("ref=ting", url)
        self.assertIn("src=line", url)
        self.assertIn("campaign=income01", url)
        self.assertIn("entry=friend", url)
        self.assertIn("quiz=wealth", url)

    def test_share_pack_contains_platform_specific_copy(self):
        pack = build_partner_share_pack(
            partner_name="Rich",
            client_name="訪客",
            quiz_label="財富風格",
            result_title="領航型",
            result_summary="善於快速行動。",
            share_url="https://example.com/",
        )
        self.assertEqual(set(pack), {"line", "instagram", "facebook", "follow_up"})
        self.assertIn("Rich", pack["line"])
        self.assertIn("#自我探索", pack["instagram"])
        self.assertIn("https://example.com/", pack["facebook"])

    def test_campaign_pack_is_ready_for_partner_distribution(self):
        pack = build_campaign_share_pack(
            partner_name="Rich",
            quiz_label="財富與行動風格",
            share_url="https://example.com/?ref=rich",
        )
        self.assertEqual(set(pack), {"line", "instagram", "facebook"})
        self.assertIn("Rich", pack["line"])
        self.assertIn("完整結果直接看", pack["instagram"])

    def test_event_row_matches_declared_columns(self):
        context = AcquisitionContext.from_values(
            ref_input="master",
            source="direct",
            campaign="organic",
            entry="cold",
            forced_quiz="",
        )
        row = build_event_row(
            now_text="2026-07-23 12:00:00",
            session_id="abc",
            event="result_viewed",
            context=context,
            ref_resolved="master",
            partner_name="Rich",
            quiz_id="wealth",
            step=10,
            meta={"result": "A"},
        )
        self.assertEqual(list(row), EVENT_COLUMNS)
        self.assertEqual(row["entry"], "cold")
        self.assertIn('"result": "A"', row["meta"])

    def test_events_csv_header_matches_event_contract(self):
        header = Path("events_header.csv").read_text(encoding="utf-8").strip().split(",")
        self.assertEqual(header, EVENT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
