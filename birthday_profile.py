"""Pure scoring helpers for the birthday-energy and action-style quiz.

The birthday-energy layer is a lightweight self-reflection prompt.  The action
style layer uses ten original, Big-Five-inspired behavioural statements.  It is
not a clinical or diagnostic assessment.
"""

from __future__ import annotations

import calendar
from typing import Any, Dict, Mapping


DIMENSION_ORDER = ["O", "C", "E", "A", "S"]

DIMENSION_PROFILES = {
    "O": {
        "label": "靈感探索",
        "prefix": "靈感型",
        "summary": "你會從新點子與不同視角中找到能量，適合先看見可能性，再挑一個方向落地。",
        "strength": "能快速連結新觀點，替團隊打開不同的可能。",
        "blind_spot": "點子一多，容易同時開太多條線，最後分散了完成度。",
        "action": "把今天最有感的一個點子，縮成 15 分鐘內能完成的第一步。",
    },
    "C": {
        "label": "穩定執行",
        "prefix": "實踐型",
        "summary": "你重視承諾、順序與完成度，最能把模糊想法一步步變成可見成果。",
        "strength": "能建立節奏、守住品質，讓好想法真正被完成。",
        "blind_spot": "太想準備完整時，可能把開始時間往後延，或對自己要求過高。",
        "action": "選一件最重要的事，先排出今天可完成的 20 分鐘版本。",
    },
    "E": {
        "label": "主動連結",
        "prefix": "發光型",
        "summary": "你在交流與行動中更容易產生能量，適合透過開口、示範與互動推動事情。",
        "strength": "敢於開啟對話，也能讓現場更有動能與參與感。",
        "blind_spot": "推進太快時，可能還沒聽完自己或別人的真實需求。",
        "action": "今天主動聯絡一個人，先問一個真誠問題，再分享你的想法。",
    },
    "A": {
        "label": "同理協作",
        "prefix": "共好型",
        "summary": "你能感受到他人的在意，擅長建立信任，讓合作在被理解的氣氛裡發生。",
        "strength": "能聽懂話語背後的需要，替關係找到雙方都舒服的位置。",
        "blind_spot": "太照顧他人時，可能晚了一步說出自己的界線與需求。",
        "action": "在答應下一件事前，先說出你需要的時間、資源或界線。",
    },
    "S": {
        "label": "沉著韌性",
        "prefix": "沉著型",
        "summary": "你在變化中較能穩住自己，適合先釐清現況，再用可持續的節奏處理壓力。",
        "strength": "遇到壓力仍能保留判斷空間，替自己與他人穩住節奏。",
        "blind_spot": "習慣自己消化時，別人可能看不見你其實也需要支持。",
        "action": "寫下現在最擔心的事，以及一個你能控制、一個可以求助的部分。",
    },
}


ACTION_CHOICES = [
    ("非常不像我", 1),
    ("比較不像我", 2),
    ("比較像我", 3),
    ("非常像我", 4),
]


ACTION_QUESTIONS = [
    {
        "id": "B01",
        "dimension": "O",
        "reverse": False,
        "text": "遇到新工具或新方法，我通常會想先玩玩看。",
    },
    {
        "id": "B02",
        "dimension": "C",
        "reverse": False,
        "text": "答應的事，我通常會排進行程並做到。",
    },
    {
        "id": "B03",
        "dimension": "E",
        "reverse": False,
        "text": "進入陌生場合，我通常願意先開口。",
    },
    {
        "id": "B04",
        "dimension": "A",
        "reverse": False,
        "text": "意見不同時，我會先理解對方真正重視什麼。",
    },
    {
        "id": "B05",
        "dimension": "S",
        "reverse": False,
        "text": "壓力來時，我多半能先穩住，再處理問題。",
    },
    {
        "id": "B06",
        "dimension": "O",
        "reverse": True,
        "text": "熟悉的方法比較安心，我很少主動嘗試新的做法。",
    },
    {
        "id": "B07",
        "dimension": "C",
        "reverse": True,
        "text": "事情一多，我常做到一半就轉去處理別的事。",
    },
    {
        "id": "B08",
        "dimension": "E",
        "reverse": True,
        "text": "就算有想法，我也常等別人先說。",
    },
    {
        "id": "B09",
        "dimension": "A",
        "reverse": True,
        "text": "為了把事做完，我有時會忽略別人的感受。",
    },
    {
        "id": "B10",
        "dimension": "S",
        "reverse": True,
        "text": "一點變化就容易讓我反覆擔心很久。",
    },
]


BIRTHDAY_CORES = {
    1: {
        "label": "開創者",
        "emoji": "🔥",
        "essence": "你傾向自己定方向，喜歡把第一步走出來。",
        "strengths": ["敢開始", "有主見"],
        "blind_spot": "有時會太快獨自扛下全部，忘了讓別人參與。",
    },
    2: {
        "label": "協調者",
        "emoji": "🌙",
        "essence": "你敏銳而重視關係，擅長讓不同的人靠近彼此。",
        "strengths": ["善傾聽", "會協調"],
        "blind_spot": "在意氣氛時，可能把自己的真實想法放到最後。",
    },
    3: {
        "label": "表達者",
        "emoji": "✨",
        "essence": "你透過表達、創意與分享感染別人。",
        "strengths": ["有創意", "會表達"],
        "blind_spot": "靈感很多時，容易低估持續整理與收尾的重要。",
    },
    4: {
        "label": "建造者",
        "emoji": "🧱",
        "essence": "你相信穩定累積，擅長把事情做成可靠的結構。",
        "strengths": ["重踏實", "有耐力"],
        "blind_spot": "守住秩序時，可能對突然的變動感到不自在。",
    },
    5: {
        "label": "探索者",
        "emoji": "🧭",
        "essence": "你好奇、重視自由，也願意從變化中發現機會。",
        "strengths": ["適應快", "敢探索"],
        "blind_spot": "追逐新鮮感時，可能還沒累積就想切換方向。",
    },
    6: {
        "label": "守護者",
        "emoji": "💛",
        "essence": "你有責任感，會主動照顧人與關係的需要。",
        "strengths": ["有責任感", "願照顧"],
        "blind_spot": "太習慣付出時，容易忽略自己的能量是否足夠。",
    },
    7: {
        "label": "洞察者",
        "emoji": "🔎",
        "essence": "你喜歡理解本質，會在安靜思考中形成自己的判斷。",
        "strengths": ["看得深", "善分析"],
        "blind_spot": "想得很完整時，可能錯過先試一次就能得到的答案。",
    },
    8: {
        "label": "成就者",
        "emoji": "🏆",
        "essence": "你重視成果與影響力，擅長整合資源推進目標。",
        "strengths": ["有企圖", "會整合"],
        "blind_spot": "專注成果時，可能把休息與情緒需求視為次要。",
    },
    9: {
        "label": "奉獻者",
        "emoji": "🌏",
        "essence": "你容易看見更大的意義，希望自己的行動也能幫助別人。",
        "strengths": ["有同理心", "看見全局"],
        "blind_spot": "理想很大時，可能承接太多不真正屬於你的責任。",
    },
}


def reduce_birth_energy(month: int, day: int) -> int:
    """Validate month/day and reduce their digits to a number from 1 to 9."""
    month = int(month)
    day = int(day)
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    max_day = calendar.monthrange(2000, month)[1]
    if day < 1 or day > max_day:
        raise ValueError("day is invalid for month")

    value = sum(int(char) for char in f"{month}{day}")
    while value > 9:
        value = sum(int(char) for char in str(value))
    return value


def compute_action_report(
    answers: Mapping[int, Any],
    birth_energy: int,
) -> Dict[str, Any]:
    """Return presentation-ready scores without retaining the raw birth date."""
    if int(birth_energy) not in BIRTHDAY_CORES:
        raise ValueError("birth_energy must be between 1 and 9")

    dimension_values = {key: [] for key in DIMENSION_ORDER}
    for number, question in enumerate(ACTION_QUESTIONS, start=1):
        if number not in answers:
            raise ValueError(f"missing answer {number}")
        value = int(answers[number])
        if value not in (1, 2, 3, 4):
            raise ValueError(f"invalid answer {number}")
        scored = 5 - value if question["reverse"] else value
        dimension_values[question["dimension"]].append(scored)

    raw_scores = {
        key: round(sum(values) / len(values), 2)
        for key, values in dimension_values.items()
    }
    percent_scores = {
        key: round((raw_scores[key] - 1) / 3 * 100)
        for key in DIMENSION_ORDER
    }
    ranked = sorted(
        DIMENSION_ORDER,
        key=lambda key: (-raw_scores[key], DIMENSION_ORDER.index(key)),
    )
    primary = ranked[0]
    secondary = ranked[1]
    dimension = DIMENSION_PROFILES[primary]
    core = BIRTHDAY_CORES[int(birth_energy)]

    return {
        "birth_energy": int(birth_energy),
        "core_label": core["label"],
        "core_emoji": core["emoji"],
        "core_essence": core["essence"],
        "primary": primary,
        "secondary": secondary,
        "primary_label": dimension["label"],
        "secondary_label": DIMENSION_PROFILES[secondary]["label"],
        "combined_title": f"{dimension['prefix']}{core['label']}",
        "summary": f"{core['essence']}{dimension['summary']}",
        "strengths": [
            *core["strengths"],
            dimension["strength"],
        ],
        "blind_spot": f"{core['blind_spot']}{dimension['blind_spot']}",
        "next_action": dimension["action"],
        "raw_scores": raw_scores,
        "scores": percent_scores,
    }
