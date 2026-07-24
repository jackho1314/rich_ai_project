"""Streamlit smoke tests that never connect to production services."""

from __future__ import annotations

import os
import unittest

os.environ["RICH_DEMO_MODE"] = "1"

from streamlit.testing.v1 import AppTest


APP_FILE = "app.py"


def make_app(*, entry: str = "friend", quiz: str = "wealth") -> AppTest:
    app = AppTest.from_file(APP_FILE, default_timeout=60)
    app.query_params["ref"] = "master"
    app.query_params["src"] = "line" if entry == "friend" else "ig"
    app.query_params["campaign"] = "qa"
    app.query_params["entry"] = entry
    if quiz:
        app.query_params["quiz"] = quiz
    return app


def set_result_state(app: AppTest, quiz: str) -> None:
    app.session_state["page"] = "result"
    app.session_state["quiz_id"] = quiz
    app.session_state["u_name"] = "QA訪客"
    app.session_state["u_state"] = "我想提升財富"
    if quiz == "birthday":
        app.session_state["life_path"] = 7
        app.session_state["birth_energy"] = 7
        app.session_state["birth_year"] = 1991
        app.session_state["birth_month"] = 12
        app.session_state["birth_day"] = 29
        values = [4] * 8 + [1] * 4 + [2] * 4 + [3] * 4
        app.session_state["answers_map"] = {
            index: value for index, value in enumerate(values, start=1)
        }
    elif quiz == "wealth":
        app.session_state["answers_map"] = {i: "A" for i in range(1, 11)}
    else:
        app.session_state["answers_map"] = {i: 0 for i in range(1, 11)}


class StreamlitDemoSmokeTest(unittest.TestCase):
    def test_default_entry_features_birthday_quiz(self) -> None:
        app = make_app(quiz="")
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["quiz_id"], "birthday")
        markdown = "\n".join(element.value for element in app.markdown)
        self.assertIn("很高興認識你", markdown)
        self.assertIn("＋ 加入 LINE 保持聯絡", markdown)
        self.assertIn("選一個你方便的方式", markdown)
        self.assertNotIn("自然的開場話題", markdown)
        self.assertIn("10 秒看見你的生命靈數", markdown)
        self.assertIn("想更深入了解自己，再進入 20 題人性探索", markdown)
        self.assertIn('alt="RICH TEAM"', markdown)
        self.assertIn("@keyframes richRevealUp", markdown)
        self.assertIn("@media (prefers-reduced-motion:reduce)", markdown)
        captions = "\n".join(element.value for element in app.caption)
        self.assertNotIn("只有主動同意才會建立後續名單", captions)
        self.assertNotIn(
            "🚀 請先選完整生日",
            [button.label for button in app.button],
        )

        app.selectbox(key="birth_year_select_v2").set_value(1990).run()
        app.selectbox(key="birth_month_select_v2").set_value(12).run()
        app.selectbox(key="birth_day_select_v2").set_value(29).run()
        self.assertEqual(
            app.button(key="start_btn_mobile").label,
            "🚀 立即看我的完整生命靈數",
        )
        self.assertFalse(app.button(key="start_btn_mobile").disabled)
        app.button(key="start_btn_mobile").click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["page"], "life_path_result")
        self.assertEqual(app.session_state["life_path"], 6)
        result_markdown = "\n".join(element.value for element in app.markdown)
        result_code = "\n".join(element.value for element in app.code)
        result_captions = "\n".join(element.value for element in app.caption)
        self.assertIn("6 號・守護者", result_markdown)
        self.assertIn("天生強項｜協調", result_markdown)
        self.assertIn("第一印象｜探索", result_markdown)
        self.assertIn("只有最上面的「6 號・守護者」是主要類型", result_markdown)
        self.assertIn("計算值 2", result_markdown)
        self.assertIn("計算值 5", result_markdown)
        self.assertNotIn("生日天賦｜2 號", result_markdown)
        self.assertNotIn("外在態度｜5 號", result_markdown)
        self.assertIn("今年主題", result_markdown)
        self.assertIn("不用做 20 題", result_captions)
        self.assertNotIn("1990", result_markdown)
        self.assertNotIn("1990", result_code)
        self.assertTrue(
            any(
                str(key).startswith("life_path|")
                for key in app.session_state["auto_notified_results"]
            )
        )

        app.button(key="start_humanity_btn_mobile").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["page"], "quiz")
        self.assertEqual(app.session_state["step"], 1)
        self.assertEqual(app.session_state["answers_map"], {})

    def test_three_entry_messages_render(self) -> None:
        expectations = {
            "friend": "很高興認識你",
            "cold": "你不是不努力，可能只是還沒找到適合自己的行動方式",
            "social": "快速看見你現在最值得優先調整的一步",
        }
        for entry, expected in expectations.items():
            with self.subTest(entry=entry):
                app = make_app(entry=entry)
                app.run()
                self.assertEqual(len(app.exception), 0)
                markdown = "\n".join(element.value for element in app.markdown)
                self.assertIn(expected, markdown)

    def test_quiz_requires_an_explicit_answer(self) -> None:
        app = make_app()
        app.session_state["page"] = "quiz"
        app.session_state["quiz_id"] = "wealth"
        app.session_state["step"] = 1
        app.session_state["answers_map"] = {}
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.radio), 1)
        self.assertIsNone(app.radio[0].value)
        self.assertEqual(
            [button.label for button in app.button],
            ["⬅️ 上一題", "下一題 ➡️"],
        )

    def test_mobile_start_cta_enters_quiz(self) -> None:
        app = make_app()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            app.button(key="start_btn_mobile").label,
            "🚀 開始 2 分鐘探索",
        )

        app.button(key="start_btn_mobile").click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["page"], "quiz")
        self.assertEqual(app.session_state["step"], 1)
        self.assertEqual(app.session_state["answers_map"], {})

    def test_birthday_result_is_visible_and_privacy_safe(self) -> None:
        app = make_app(entry="social", quiz="birthday")
        set_result_state(app, "birthday")
        app.run()

        self.assertEqual(len(app.exception), 0)
        markdown = "\n".join(element.value for element in app.markdown)
        code = "\n".join(element.value for element in app.code)
        self.assertIn("7號洞察者 × 大蜜蜂", markdown)
        self.assertIn("生命靈數 7 號", markdown)
        self.assertIn("完整解析", markdown)
        self.assertIn("我的生命原型", markdown)
        self.assertIn("LINE 傳給朋友", markdown)
        self.assertIn("＋ 加入侯閔議的 LINE", markdown)
        self.assertIn("https://line.me/R/share?text=", markdown)
        self.assertNotIn("12 月 29", code)
        self.assertNotIn("1991", code)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["LINE", "Instagram", "Facebook"],
        )
        self.assertNotIn(
            "同意儲存結果並通知分享夥伴",
            [button.label for button in app.button],
        )
        self.assertTrue(
            any(
                str(key).startswith("humanity|")
                for key in app.session_state["auto_notified_results"]
            )
        )

    def test_birthday_quiz_requires_an_explicit_answer(self) -> None:
        app = make_app(quiz="birthday")
        app.session_state["page"] = "quiz"
        app.session_state["quiz_id"] = "birthday"
        app.session_state["life_path"] = 5
        app.session_state["birth_energy"] = 5
        app.session_state["step"] = 1
        app.session_state["answers_map"] = {}
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.radio), 1)
        self.assertIsNone(app.radio[0].value)
        self.assertEqual(
            [button.label for button in app.button],
            ["⬅️ 上一題", "下一題 ➡️"],
        )

    def test_wealth_result_is_visible_before_opt_in(self) -> None:
        app = make_app(quiz="wealth")
        set_result_state(app, "wealth")
        app.run()

        self.assertEqual(len(app.exception), 0)
        markdown = "\n".join(element.value for element in app.markdown)
        self.assertIn("完整分析報告", markdown)
        self.assertIn("完整解析", markdown)
        self.assertIn("結果摘要", markdown)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["LINE", "Instagram", "Facebook"],
        )
        self.assertNotIn(
            "同意儲存結果並通知分享夥伴",
            [button.label for button in app.button],
        )
        self.assertTrue(
            any(
                str(key).startswith("wealth|")
                for key in app.session_state["auto_notified_results"]
            )
        )

    def test_demo_opt_in_never_writes_to_production(self) -> None:
        app = make_app(quiz="wealth")
        set_result_state(app, "wealth")
        app.run()
        app.selectbox[0].set_value(app.selectbox[0].options[1]).run()
        app.button(key="save_lead_v2_wealth").click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state["notified"])
        self.assertTrue(
            str(app.session_state["notified_lead_id"]).startswith("demo-")
        )

    def test_health_result_and_share_pack_render(self) -> None:
        app = make_app(entry="social", quiz="health")
        set_result_state(app, "health")
        app.run()

        self.assertEqual(len(app.exception), 0)
        markdown = "\n".join(element.value for element in app.markdown)
        self.assertIn("健康結果摘要", markdown)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["LINE", "Instagram", "Facebook"],
        )
        self.assertTrue(
            any(
                str(key).startswith("health|")
                for key in app.session_state["auto_notified_results"]
            )
        )


if __name__ == "__main__":
    unittest.main()
