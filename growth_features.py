"""Pure helpers for acquisition entry points, event rows, and partner share packs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping
from urllib.parse import urlencode, urlsplit, urlunsplit


ENTRY_MODES = {"friend", "cold", "social"}
QUIZ_IDS = {"birthday", "wealth", "health"}


def _clean(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


@dataclass(frozen=True)
class AcquisitionContext:
    ref_input: str
    source: str
    campaign: str
    entry: str
    forced_quiz: str

    @classmethod
    def from_values(
        cls,
        *,
        ref_input: Any,
        source: Any,
        campaign: Any,
        entry: Any,
        forced_quiz: Any,
    ) -> "AcquisitionContext":
        entry_value = _clean(entry, "friend").lower()
        quiz_value = _clean(forced_quiz).lower()
        return cls(
            ref_input=_clean(ref_input, "master").lower(),
            source=_clean(source, "direct").lower(),
            campaign=_clean(campaign, "organic"),
            entry=entry_value if entry_value in ENTRY_MODES else "friend",
            forced_quiz=quiz_value if quiz_value in QUIZ_IDS else "",
        )


def entry_copy(context: AcquisitionContext, partner_name: str) -> Dict[str, str]:
    partner = _clean(partner_name, "一位朋友")
    if context.entry == "cold":
        return {
            "eyebrow": "先看結果，不必先加 LINE",
            "title": "你不是不努力，可能只是還沒找到適合自己的行動方式",
            "subtitle": "用一份簡短測驗，看見你的優勢、卡點與下一步。結果會直接完整顯示。",
            "partner_kicker": "結果解讀夥伴",
            "start_label": "開始了解自己",
        }
    if context.entry == "social":
        source_label = context.source.upper() if context.source != "direct" else "社群"
        return {
            "eyebrow": f"來自 {source_label} 的 2 分鐘探索",
            "title": "快速看見你現在最值得優先調整的一步",
            "subtitle": "免註冊、結果直接看；完成後也可以把結果分享給朋友。",
            "partner_kicker": "內容分享夥伴",
            "start_label": "立即看我的結果",
        }
    return {
        "eyebrow": f"{partner} 特別分享給你",
        "title": "先了解自己，再決定下一步怎麼走",
        "subtitle": "這不是推銷表單。完成後會直接看到完整解析，再由你決定是否聯絡分享人。",
        "partner_kicker": "分享這份測驗給你的人",
            "start_label": "開始 2 分鐘探索",
    }


def build_share_url(base_url: str, context: AcquisitionContext, quiz_id: str) -> str:
    base = _clean(base_url)
    if not base:
        return ""
    parts = urlsplit(base)
    query = urlencode(
        {
            "ref": context.ref_input,
            "src": context.source,
            "campaign": context.campaign,
            "entry": context.entry,
            "quiz": quiz_id if quiz_id in QUIZ_IDS else "",
        }
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", query, ""))


def build_partner_share_pack(
    *,
    partner_name: str,
    client_name: str,
    quiz_label: str,
    result_title: str,
    result_summary: str,
    share_url: str,
) -> Dict[str, str]:
    partner = _clean(partner_name, "我")
    client = _clean(client_name, "我")
    quiz = _clean(quiz_label, "成長風格")
    result = _clean(result_title, "我的個人化結果")
    summary = _clean(result_summary, "測完會直接看到完整解析與下一步。")
    url_line = f"\n{share_url}" if share_url else ""

    line = (
        f"我剛完成「{quiz}」，結果是：{result}。\n"
        f"{summary}\n\n"
        f"這份測驗是 {partner} 分享給我的，結果會直接顯示，不用先加好友。"
        f"{url_line}"
    )
    instagram = (
        f"我的 {quiz}：{result} ✨\n"
        f"{summary}\n\n"
        "想知道你適合哪一種行動方式？到個人簡介連結測測看。\n"
        "#自我探索 #行動風格 #AI工具"
    )
    facebook = (
        f"原來我在「{quiz}」裡屬於：{result}。\n\n"
        f"{summary}\n\n"
        "我喜歡它的一點是：結果會先完整顯示，再由自己決定要不要找人討論。"
        f"{url_line}"
    )
    follow_up = (
        f"嗨 {client}，謝謝你完成測驗。你的結果是「{result}」。"
        "你最有感的是哪一段？如果願意，我可以只針對那一段陪你整理下一步。"
    )
    return {
        "line": line,
        "instagram": instagram,
        "facebook": facebook,
        "follow_up": follow_up,
    }


def build_campaign_share_pack(
    *,
    partner_name: str,
    quiz_label: str,
    share_url: str,
) -> Dict[str, str]:
    partner = _clean(partner_name, "我")
    quiz = _clean(quiz_label, "成長探索")
    url_line = f"\n{share_url}" if share_url else ""
    return {
        "line": (
            f"嗨，我是 {partner}。我最近在使用一份「{quiz}」，"
            "可以快速整理自己的優勢、卡點與下一步。\n\n"
            "它會先直接顯示完整結果，不需要先加好友；有空可以玩玩看。"
            f"{url_line}"
        ),
        "instagram": (
            f"2 分鐘看見你的「{quiz}」✨\n"
            "完整結果直接看｜免註冊｜由你決定要不要繼續聊\n\n"
            "測驗連結放在個人簡介／限動連結。\n"
            "#自我探索 #行動風格 #成長工具"
        ),
        "facebook": (
            "你有沒有過這種感覺：很努力，卻不知道下一步應該先做什麼？\n\n"
            f"我整理了一份「{quiz}」，幫你快速看見自己的行動優勢與卡點。"
            "結果會直接完整顯示，不會先要求你加好友。"
            f"{url_line}"
        ),
    }


EVENT_COLUMNS = [
    "time",
    "session_id",
    "event",
    "ref_input",
    "ref_resolved",
    "partner_name",
    "source",
    "campaign",
    "entry",
    "quiz_id",
    "step",
    "lead_id",
    "meta",
]


def build_event_row(
    *,
    now_text: str,
    session_id: str,
    event: str,
    context: AcquisitionContext,
    ref_resolved: str,
    partner_name: str,
    quiz_id: str = "",
    step: Any = "",
    lead_id: str = "",
    meta: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    return {
        "time": _clean(now_text),
        "session_id": _clean(session_id),
        "event": _clean(event),
        "ref_input": context.ref_input,
        "ref_resolved": _clean(ref_resolved),
        "partner_name": _clean(partner_name),
        "source": context.source,
        "campaign": context.campaign,
        "entry": context.entry,
        "quiz_id": _clean(quiz_id),
        "step": _clean(step),
        "lead_id": _clean(lead_id),
        "meta": json.dumps(dict(meta or {}), ensure_ascii=False, sort_keys=True),
    }
