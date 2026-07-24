"""Stable scoring module for the life-path and Mini-IPIP exploration.

The life-path layer is a numerology-inspired reflection prompt.  The 20-item
layer follows the public-domain Mini-IPIP five-factor structure; its animal
labels are a local storytelling layer rather than validated personality types.
Neither layer is a psychological, medical, or clinical diagnosis.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, Mapping, Optional


ANIMAL_ORDER = [1, 2, 3, 4]

ANIMAL_PROFILES = {
    1: {
        "code": "tiger",
        "label": "老虎",
        "emoji": "🐯",
        "short": "先抓目標、快速判斷並推動事情",
        "summary": "你習慣抓住目標、快速判斷，遇到需要推進的時刻通常願意站到前面。",
        "team_strength": "定方向、做決策、在壓力下把團隊往成果推進。",
        "blind_spot": "速度與標準一拉高，可能讓較慢熱的人來不及說出顧慮。",
        "collaboration": "先講目標、期限與決策範圍，再直接提供可選方案與關鍵風險。",
        "action": "下一次要定案前，多問一句：「還有哪個風險是我現在沒看到的？」",
    },
    2: {
        "code": "dolphin",
        "label": "海豚",
        "emoji": "🐬",
        "short": "用互動、表達與連結帶動參與",
        "summary": "你重視互動與感受，能用熱情、故事和連結讓人願意參與。",
        "team_strength": "創造氣氛、凝聚關係、把抽象想法說得有感染力。",
        "blind_spot": "靈感與人際訊號很多時，容易低估細節、時間或收尾。",
        "collaboration": "先讓你理解願景與人的意義，再一起把想法收斂成清楚里程碑。",
        "action": "把今天最有感的點子，寫成一個負責人、一個期限與一個完成標準。",
    },
    3: {
        "code": "penguin",
        "label": "企鵝",
        "emoji": "🐧",
        "short": "以傾聽、耐心與支持維持合作",
        "summary": "你重視穩定、信任與和諧，願意傾聽並用耐心守住合作節奏。",
        "team_strength": "穩定團隊、照顧關係、持續把已承諾的事做好。",
        "blind_spot": "為了避免衝突或變動，可能太晚說出不同意見與自己的需求。",
        "collaboration": "提早說明變動原因、給準備時間，並主動邀請你說出真實看法。",
        "action": "在下一次配合別人前，先清楚說出一個你的需求或界線。",
    },
    4: {
        "code": "bee",
        "label": "蜜蜂",
        "emoji": "🐝",
        "short": "先釐清資料與方法，再守住品質",
        "summary": "你重視正確、品質與方法，會先釐清資料，再用可靠流程完成事情。",
        "team_strength": "分析風險、建立標準、找出細節中的漏洞並守住品質。",
        "blind_spot": "資料還不夠完整時，可能反覆分析，讓決策與嘗試延後。",
        "collaboration": "提供背景、數據與品質標準，也明確說明何時需要先做小規模試驗。",
        "action": "替正在分析的事設定停止條件，資料到 70% 就先做一個低風險測試。",
    },
    "octopus": {
        "code": "octopus",
        "label": "八爪",
        "emoji": "🐙",
        "short": "依情境彈性切換互動與行動方式",
        "summary": "你的四種傾向相對平均，會依人、情境與任務彈性切換做法。",
        "team_strength": "能讀懂不同角色、補位協調，並在多種溝通方式之間轉換。",
        "blind_spot": "太常配合情境時，別人可能看不清你的優先順序，你也容易同時承接太多。",
        "collaboration": "先一起確認此刻最重要的角色與一項成果，避免所有需求都由你補位。",
        "action": "今天只選一個你最需要扮演的角色，並說明其他事情暫時不接。",
    },
}


LIFE_PATH_PROFILES = {
    1: {
        "label": "開創者",
        "emoji": "🔥",
        "essence": "你的內在動力偏向自主、開創與率先行動。",
        "strengths": ["敢開始", "有主見"],
        "blind_spot": "有時會太快獨自扛下全部，忘了讓別人參與。",
    },
    2: {
        "label": "協調者",
        "emoji": "🌙",
        "essence": "你的內在動力來自連結、合作與細膩感受。",
        "strengths": ["善傾聽", "會協調"],
        "blind_spot": "在意氣氛時，可能把自己的真實想法放到最後。",
    },
    3: {
        "label": "表達者",
        "emoji": "✨",
        "essence": "你的內在動力來自表達、創意與分享。",
        "strengths": ["有創意", "會表達"],
        "blind_spot": "靈感很多時，容易低估持續整理與收尾的重要。",
    },
    4: {
        "label": "建造者",
        "emoji": "🧱",
        "essence": "你的內在動力來自秩序、累積與可靠成果。",
        "strengths": ["重踏實", "有耐力"],
        "blind_spot": "守住秩序時，可能對突然的變動感到不自在。",
    },
    5: {
        "label": "探索者",
        "emoji": "🧭",
        "essence": "你的內在動力來自自由、變化與新鮮體驗。",
        "strengths": ["適應快", "敢探索"],
        "blind_spot": "追逐新鮮感時，可能還沒累積就想切換方向。",
    },
    6: {
        "label": "守護者",
        "emoji": "💛",
        "essence": "你的內在動力來自責任、照顧與關係承諾。",
        "strengths": ["有責任感", "願照顧"],
        "blind_spot": "太習慣付出時，容易忽略自己的能量是否足夠。",
    },
    7: {
        "label": "洞察者",
        "emoji": "🔎",
        "essence": "你的內在動力來自理解本質、獨立思考與深度。",
        "strengths": ["看得深", "善分析"],
        "blind_spot": "想得很完整時，可能錯過先試一次就能得到的答案。",
    },
    8: {
        "label": "成就者",
        "emoji": "🏆",
        "essence": "你的內在動力來自成果、影響力與資源整合。",
        "strengths": ["有企圖", "會整合"],
        "blind_spot": "專注成果時，可能把休息與情緒需求視為次要。",
    },
    9: {
        "label": "奉獻者",
        "emoji": "🌏",
        "essence": "你的內在動力來自意義、同理與更大的共同利益。",
        "strengths": ["有同理心", "看見全局"],
        "blind_spot": "理想很大時，可能承接太多不真正屬於你的責任。",
    },
}

# Keep the old public name for existing integrations while the UI migrates.
BIRTHDAY_CORES = LIFE_PATH_PROFILES


NUMBER_THEMES = {
    1: {
        "label": "開創",
        "gift": "主動、自主、敢先開始",
        "approach": "遇到新情境時，傾向先抓方向並採取行動。",
        "practice": "練習邀請別人參與，而不是凡事自己扛。",
        "year_focus": "啟動與重新定位",
        "year_action": "選一件最想開始的事，先做出第一個可見版本。",
    },
    2: {
        "label": "協調",
        "gift": "感受、傾聽、連結關係",
        "approach": "遇到新情境時，會先觀察氣氛與彼此需求。",
        "practice": "在照顧關係時，也清楚說出自己的立場。",
        "year_focus": "合作與耐心醞釀",
        "year_action": "找一位可信任的人，把想法透過合作慢慢做深。",
    },
    3: {
        "label": "表達",
        "gift": "創意、樂觀、傳遞想法",
        "approach": "遇到新情境時，會透過互動與表達找到可能性。",
        "practice": "把好點子收斂成一個期限與完成標準。",
        "year_focus": "表達與被看見",
        "year_action": "公開分享一個作品、觀點或真實感受。",
    },
    4: {
        "label": "建造",
        "gift": "秩序、務實、穩定累積",
        "approach": "遇到新情境時，會先確認規則、資源與可行步驟。",
        "practice": "保留一點彈性，允許先試再調整。",
        "year_focus": "打底與建立系統",
        "year_action": "替重要目標建立一個每週能持續的固定節奏。",
    },
    5: {
        "label": "探索",
        "gift": "彈性、好奇、快速適應",
        "approach": "遇到新情境時，會先尋找變化、選項與自由空間。",
        "practice": "在切換方向前，先完成一個可驗證的小成果。",
        "year_focus": "改變與拓展經驗",
        "year_action": "安排一次有邊界的新嘗試，擴大經驗而不失控。",
    },
    6: {
        "label": "守護",
        "gift": "責任、照顧、創造歸屬",
        "approach": "遇到新情境時，會先確認人是否被照顧、承諾是否穩定。",
        "practice": "付出之前先檢查自己的能量與界線。",
        "year_focus": "關係、承諾與生活品質",
        "year_action": "修復一段重要關係，或改善一個每天都會接觸的環境。",
    },
    7: {
        "label": "洞察",
        "gift": "研究、思辨、理解本質",
        "approach": "遇到新情境時，會先退一步觀察、蒐集與理解。",
        "practice": "不用等到完全確定，先用低風險方式驗證想法。",
        "year_focus": "沉澱、學習與內在整理",
        "year_action": "固定留一段不被打擾的時間，深化真正重要的問題。",
    },
    8: {
        "label": "成就",
        "gift": "整合、企圖、推動成果",
        "approach": "遇到新情境時，會先衡量目標、資源與影響力。",
        "practice": "成果之外，也把人的感受與長期代價納入決策。",
        "year_focus": "成果、資源與影響力",
        "year_action": "把一個重要目標量化，並每週檢查最關鍵的進度。",
    },
    9: {
        "label": "奉獻",
        "gift": "同理、格局、看見共同利益",
        "approach": "遇到新情境時，會先看整體意義與對他人的影響。",
        "practice": "分辨同理與過度承擔，保留自己的界線。",
        "year_focus": "完成、整理與放下",
        "year_action": "完成一件拖延已久的事，替下一個循環騰出空間。",
    },
}


def _reduce_to_digit(value: int) -> int:
    value = abs(int(value))
    while value > 9:
        value = sum(int(char) for char in str(value))
    return value


LIKERT_OPTIONS = [
    ("1　很不像我", 1),
    ("2　比較不像我", 2),
    ("3　一半一半", 3),
    ("4　比較像我", 4),
    ("5　很像我", 5),
]


TRAIT_PROFILES = {
    "E": {
        "label": "外向互動",
        "high": "主動表達",
        "middle": "彈性互動",
        "low": "沉靜觀察",
    },
    "A": {
        "label": "同理合作",
        "high": "同理合作",
        "middle": "合作有界線",
        "low": "獨立直率",
    },
    "C": {
        "label": "規劃執行",
        "high": "規劃執行",
        "middle": "依情境規劃",
        "low": "彈性即興",
    },
    "ES": {
        "label": "情緒穩定",
        "high": "沉著穩定",
        "middle": "情境調節",
        "low": "敏銳反應",
    },
    "O": {
        "label": "開放探索",
        "high": "探索創新",
        "middle": "彈性整合",
        "low": "務實聚焦",
    },
}


# Traditional-Chinese pilot adaptation of the public-domain Mini-IPIP.
# Keep the original five-factor item order and reverse-key structure.  Local
# reliability and validity should be checked before calling it a Taiwan norm.
HUMANITY_QUESTIONS = [
    {
        "id": "MIPIP01",
        "text": "在聚會或團體中，我常能帶動現場氣氛。",
        "trait": "E",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP02",
        "text": "我能理解並關心別人的感受。",
        "trait": "A",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP03",
        "text": "該做的事情，我通常會很快開始處理。",
        "trait": "C",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP04",
        "text": "我的情緒容易在短時間內出現起伏。",
        "trait": "ES",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP05",
        "text": "我很容易在腦中想像出畫面或新的點子。",
        "trait": "O",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP06",
        "text": "我平常不太主動說話。",
        "trait": "E",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP07",
        "text": "別人遇到問題時，我通常不會投入太多注意力。",
        "trait": "A",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP08",
        "text": "我常忘記把用過的東西放回原位。",
        "trait": "C",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP09",
        "text": "大部分時間，我能保持放鬆。",
        "trait": "ES",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP10",
        "text": "我對抽象概念或理論通常沒有興趣。",
        "trait": "O",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP11",
        "text": "聚會時，我會主動和許多不同的人聊天。",
        "trait": "E",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP12",
        "text": "我很容易察覺並感受到別人的情緒。",
        "trait": "A",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP13",
        "text": "我喜歡事情安排得井然有序。",
        "trait": "C",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP14",
        "text": "遇到不順心的事情時，我很容易煩躁。",
        "trait": "ES",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP15",
        "text": "我不太容易理解抽象或概念性的想法。",
        "trait": "O",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP16",
        "text": "在團體中，我通常待在比較不顯眼的位置。",
        "trait": "E",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP17",
        "text": "我通常不太想深入了解其他人。",
        "trait": "A",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP18",
        "text": "我常把事情或周遭環境弄得有些混亂。",
        "trait": "C",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP19",
        "text": "我很少長時間感到低落。",
        "trait": "ES",
        "reverse": False,
        "options": LIKERT_OPTIONS,
    },
    {
        "id": "MIPIP20",
        "text": "我的想像力不算豐富。",
        "trait": "O",
        "reverse": True,
        "options": LIKERT_OPTIONS,
    },
]


def calculate_life_path(year: int, month: int, day: int) -> int:
    """Validate a full Gregorian birth date and reduce all digits to 1–9."""
    year = int(year)
    month = int(month)
    day = int(day)
    birth_date = date(year, month, day)
    if birth_date > date.today():
        raise ValueError("birth date cannot be in the future")

    value = sum(int(char) for char in f"{year:04d}{month:02d}{day:02d}")
    return _reduce_to_digit(value)


def build_life_path_report(
    year: int,
    month: int,
    day: int,
    *,
    current_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a richer, raw-date-free reflection report from one birth date.

    The returned mapping deliberately excludes the original year, month and day
    so it can be used by the UI, sharing and analytics without retaining the
    visitor's full birth date.
    """
    year = int(year)
    month = int(month)
    day = int(day)
    birth_date = date(year, month, day)
    if birth_date > date.today():
        raise ValueError("birth date cannot be in the future")

    report_year = int(current_year or date.today().year)
    if report_year < 1:
        raise ValueError("current_year must be positive")

    life_path = calculate_life_path(year, month, day)
    birthday_number = _reduce_to_digit(day)
    attitude_number = _reduce_to_digit(month + day)
    month_number = _reduce_to_digit(month)
    generation_number = _reduce_to_digit(year)
    personal_year = _reduce_to_digit(month + day + report_year)

    birth_digits = [
        int(char)
        for char in f"{year:04d}{month:02d}{day:02d}"
        if char != "0"
    ]
    digit_counts = Counter(birth_digits)
    repeated_numbers = [
        {
            "number": number,
            "count": int(digit_counts[number]),
            "label": NUMBER_THEMES[number]["label"],
            "gift": NUMBER_THEMES[number]["gift"],
        }
        for number in range(1, 10)
        if digit_counts[number] > 1
    ]
    repeated_numbers.sort(key=lambda item: (-item["count"], item["number"]))
    missing_numbers = [
        number for number in range(1, 10) if digit_counts[number] == 0
    ]

    core = LIFE_PATH_PROFILES[life_path]
    birthday_theme = NUMBER_THEMES[birthday_number]
    attitude_theme = NUMBER_THEMES[attitude_number]
    month_theme = NUMBER_THEMES[month_number]
    generation_theme = NUMBER_THEMES[generation_number]
    personal_theme = NUMBER_THEMES[personal_year]

    if life_path == attitude_number:
        cross_insight = (
            f"你的內在主軸與面對新情境的方式都偏向「{core['label']}」，"
            "通常內外感受較一致；仍可留意不要把熟悉做法用在所有情境。"
        )
    else:
        cross_insight = (
            f"你的長期內在主軸偏向「{core['label']}」，"
            f"但剛進入新情境時，會先展現「{attitude_theme['label']}」能量。"
            "別人第一眼看見的你，可能和熟悉之後不完全相同。"
        )

    repeated_text = "、".join(
        f"{item['number']}（{item['count']}次）" for item in repeated_numbers[:3]
    )
    if not repeated_text:
        repeated_text = "分布平均，沒有特別集中的數字"

    return {
        "life_path": life_path,
        "core_label": core["label"],
        "core_emoji": core["emoji"],
        "core_essence": core["essence"],
        "core_strengths": list(core["strengths"]),
        "core_blind_spot": core["blind_spot"],
        "birthday_number": birthday_number,
        "birthday_label": birthday_theme["label"],
        "birthday_gift": birthday_theme["gift"],
        "attitude_number": attitude_number,
        "attitude_label": attitude_theme["label"],
        "attitude_approach": attitude_theme["approach"],
        "attitude_practice": attitude_theme["practice"],
        "month_number": month_number,
        "month_label": month_theme["label"],
        "month_gift": month_theme["gift"],
        "generation_number": generation_number,
        "generation_label": generation_theme["label"],
        "generation_gift": generation_theme["gift"],
        "personal_year": personal_year,
        "personal_year_label": personal_theme["label"],
        "personal_year_focus": personal_theme["year_focus"],
        "personal_year_action": personal_theme["year_action"],
        "report_year": report_year,
        "repeated_numbers": repeated_numbers,
        "repeated_text": repeated_text,
        "missing_numbers": missing_numbers,
        "missing_themes": [
            {
                "number": number,
                "label": NUMBER_THEMES[number]["label"],
                "practice": NUMBER_THEMES[number]["practice"],
            }
            for number in missing_numbers
        ],
        "cross_insight": cross_insight,
        "summary": (
            f"你是 {life_path} 號{core['label']}；"
            f"天生強項偏向{birthday_theme['label']}，"
            f"面對新情境時常先展現{attitude_theme['label']}特質。"
        ),
        "next_action": personal_theme["year_action"],
    }


def _trait_band(trait: str, score: int) -> str:
    profile = TRAIT_PROFILES[trait]
    if score >= 70:
        return str(profile["high"])
    if score <= 35:
        return str(profile["low"])
    return str(profile["middle"])


def _combined_animal_profile(
    primary_value: int,
    secondary_value: int,
    *,
    is_dual: bool,
) -> Dict[str, str]:
    primary = ANIMAL_PROFILES[primary_value]
    secondary = ANIMAL_PROFILES[secondary_value]
    if is_dual:
        summary = (
            "你會依情境在兩種核心風格之間切換："
            f"{primary['short']}，也會{secondary['short']}。"
        )
    else:
        summary = (
            f"你平常較常{primary['short']}，"
            f"並用{secondary['short']}補充。"
        )
    return {
        "summary": summary,
        "team_strength": (
            f"{primary['team_strength']}同時也能運用{secondary['label']}的優勢："
            f"{secondary['team_strength']}"
        ),
        "blind_spot": (
            f"{primary['blind_spot']}當你切換到{secondary['label']}風格時，"
            f"也要留意：{secondary['blind_spot']}"
        ),
        "collaboration": (
            f"{primary['collaboration']}需要補充時，也可以："
            f"{secondary['collaboration']}"
        ),
        "action": str(primary["action"]),
    }


def compute_humanity_report(
    answers: Mapping[int, Any],
    life_path: int,
) -> Dict[str, Any]:
    """Score the Mini-IPIP pilot and return a raw-date-free report."""
    life_path = int(life_path)
    if life_path not in LIFE_PATH_PROFILES:
        raise ValueError("life_path must be between 1 and 9")

    trait_values: Dict[str, list[int]] = {
        trait: [] for trait in TRAIT_PROFILES
    }
    for number, question in enumerate(HUMANITY_QUESTIONS, start=1):
        if number not in answers:
            raise ValueError(f"missing answer {number}")
        value = int(answers[number])
        if value < 1 or value > 5:
            raise ValueError(f"invalid answer {number}")
        scored_value = 6 - value if question["reverse"] else value
        trait_values[str(question["trait"])].append(scored_value)

    if any(len(values) != 4 for values in trait_values.values()):
        raise ValueError("each Mini-IPIP trait must contain four answers")

    trait_averages = {
        trait: round(sum(values) / len(values), 2)
        for trait, values in trait_values.items()
    }
    trait_scores = {
        trait: int(round((average - 1) / 4 * 100))
        for trait, average in trait_averages.items()
    }
    trait_display_scores = {
        str(TRAIT_PROFILES[trait]["label"]): trait_scores[trait]
        for trait in TRAIT_PROFILES
    }
    trait_descriptions = {
        str(TRAIT_PROFILES[trait]["label"]): _trait_band(
            trait,
            trait_scores[trait],
        )
        for trait in TRAIT_PROFILES
    }

    expressive = float(trait_scores["E"])
    reserved = 100.0 - expressive
    people_focus = max(
        0.0,
        min(
            100.0,
            50.0 + (trait_scores["A"] - trait_scores["C"]) / 2.0,
        ),
    )
    task_focus = 100.0 - people_focus
    score_by_value = {
        1: int(round((expressive + task_focus) / 2.0)),
        2: int(round((expressive + people_focus) / 2.0)),
        3: int(round((reserved + people_focus) / 2.0)),
        4: int(round((reserved + task_focus) / 2.0)),
    }
    ranked_values = sorted(
        ANIMAL_ORDER,
        key=lambda value: (-score_by_value[value], value),
    )
    max_score = score_by_value[ranked_values[0]]
    min_score = score_by_value[ranked_values[-1]]

    if max_score - min_score < 10:
        animal_profile = dict(ANIMAL_PROFILES["octopus"])
        animal_title = "八爪平衡型"
        animal_emoji = animal_profile["emoji"]
        intensity = "balanced"
        primary = "octopus"
        secondary = ""
        is_mixed = False
        primary_label = animal_title
        secondary_label = ""
        animal_balance_label = "四種風格分布接近"
    else:
        primary_value, secondary_value = ranked_values[:2]
        primary_profile = ANIMAL_PROFILES[primary_value]
        secondary_profile = ANIMAL_PROFILES[secondary_value]
        score_gap = score_by_value[primary_value] - score_by_value[secondary_value]
        is_mixed = score_gap < 15
        animal_title = (
            f"{primary_profile['label']} × {secondary_profile['label']}"
        )
        animal_emoji = (
            f"{primary_profile['emoji']}{secondary_profile['emoji']}"
        )
        animal_profile = _combined_animal_profile(
            primary_value,
            secondary_value,
            is_dual=is_mixed,
        )
        intensity = "dual" if is_mixed else "primary"
        primary = str(primary_profile["code"])
        secondary = str(secondary_profile["code"])
        primary_label = str(primary_profile["label"])
        secondary_label = str(secondary_profile["label"])
        animal_balance_label = (
            "雙核心風格"
            if is_mixed
            else f"{primary_label}為主・{secondary_label}為輔"
        )

    core = LIFE_PATH_PROFILES[life_path]
    scores = {
        ANIMAL_PROFILES[value]["label"]: score_by_value[value]
        for value in ANIMAL_ORDER
    }
    modifier_tags = [
        trait_descriptions[str(TRAIT_PROFILES["O"]["label"])],
        trait_descriptions[str(TRAIT_PROFILES["ES"]["label"])],
    ]

    return {
        "scoring_model": "mini_ipip_zh_tw_pilot_v1",
        "life_path": life_path,
        "birth_energy": life_path,
        "core_label": core["label"],
        "core_emoji": core["emoji"],
        "core_essence": core["essence"],
        "primary": primary,
        "secondary": secondary,
        "primary_label": primary_label,
        "secondary_label": secondary_label,
        "animal_title": animal_title,
        "animal_emoji": animal_emoji,
        "animal_intensity": intensity,
        "is_mixed": is_mixed,
        "max_animal_score": max_score,
        "animal_balance_label": animal_balance_label,
        "combined_title": f"{life_path}號{core['label']}｜{animal_title}",
        "summary": (
            f"{core['essence']}20 題自評顯示，你目前的團隊互動最接近"
            f"「{animal_title}」：{animal_profile['summary']}"
        ),
        "strengths": [*core["strengths"], animal_profile["team_strength"]],
        "team_strength": animal_profile["team_strength"],
        "blind_spot": f"{core['blind_spot']}{animal_profile['blind_spot']}",
        "collaboration": animal_profile["collaboration"],
        "next_action": animal_profile["action"],
        "trait_averages": trait_averages,
        "trait_scores": trait_display_scores,
        "trait_descriptions": trait_descriptions,
        "modifier_tags": modifier_tags,
        "animal_scores": scores,
        "counts": scores,
        "scores": scores,
        "method_note": (
            "五項分數依 Mini-IPIP 架構換算為 0–100，並非人口百分位；"
            "動物名稱是方便理解的互動風格摘要。"
        ),
    }
