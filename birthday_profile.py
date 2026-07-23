"""Pure scoring helpers for the life-path and humanity-animal quiz.

The life-path layer is a numerology-inspired reflection prompt.  The 20-item
humanity layer describes communication preferences in a team.  Neither layer
is a psychological, medical, or scientific diagnosis.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, Mapping


ANIMAL_ORDER = [1, 2, 3, 4]

ANIMAL_PROFILES = {
    1: {
        "code": "tiger",
        "label": "老虎",
        "emoji": "🐯",
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


HUMANITY_QUESTIONS = [
    {
        "id": "HUM01",
        "text": "當你和朋友一起用餐時，在選擇用餐或是吃什麼時，你常是：",
        "options": [
            ("決定者：意見不同時，通常都是決定者", 1),
            ("氣氛製造者：吃什麼，很能帶動情緒氣氛", 2),
            ("附和者：隨便，沒意見", 3),
            ("意見提供者：常去否定別人的提議，自己卻又沒意見，也不做任何決定", 4),
        ],
    },
    {
        "id": "HUM02",
        "text": "當你買衣服時，你是：",
        "options": [
            ("不易受售貨員影響，「心中自有定見」", 1),
            ("售貨員的親切及好的感受，常會促進你的購買", 2),
            ("找熟悉的店購買", 3),
            ("品質與價錢是否成比例，價錢是否合理？", 4),
        ],
    },
    {
        "id": "HUM03",
        "text": "你的消費習慣是：",
        "options": [
            ("找到要買的東西，付錢走人", 1),
            ("很隨意地逛，不特定買什麼", 2),
            ("有一定的消費習慣，不太喜歡變化", 3),
            ("較注意東西好不好，較有成本觀念", 4),
        ],
    },
    {
        "id": "HUM04",
        "text": "你的朋友，以一句話來形容你，他們會說：",
        "options": [
            ("蠻「鴨霸」的", 1),
            ("熱情洋溢", 2),
            ("溫和斯文", 3),
            ("要求完美", 4),
        ],
    },
    {
        "id": "HUM05",
        "text": "你自認哪一種形容，最能表現你的特色：",
        "options": [
            ("果敢的，能接受挑戰", 1),
            ("生動活潑，不拘小節", 2),
            ("愛傾聽，喜歡穩定", 3),
            ("處世謹慎小心，重數據分析", 4),
        ],
    },
    {
        "id": "HUM06",
        "text": "你覺得做事的重點，應該是：",
        "options": [
            ("做什麼？重結果", 1),
            ("誰來做？重感受（過程）", 2),
            ("為何做？重品質", 3),
            ("怎麼做？重執行", 4),
        ],
    },
    {
        "id": "HUM07",
        "text": "與同事有意見衝突（或不同）時，你是：",
        "options": [
            ("說服對方，聽從自己的意見", 1),
            ("問其他同事或上司之意見，尋求支持", 2),
            ("退讓，以和為貴", 3),
            ("與衝突者協調，找尋最好的意見", 4),
        ],
    },
    {
        "id": "HUM08",
        "text": "什麼樣的工作環境，最能鼓舞你：",
        "options": [
            ("能讓你決定事情，具領導地位的", 1),
            ("同事相處愉快，處處受歡迎", 2),
            ("穩定中求發展", 3),
            ("講品質，重效率的工作", 4),
        ],
    },
    {
        "id": "HUM09",
        "text": "以下的溝通方式，哪一項最符合你：",
        "options": [
            ("直接了當，較權威式的", 1),
            ("表情豐富，肢體語言較多", 2),
            ("先聽別人意見，而後溫和表達自己的意見", 3),
            ("不露感情，理多於情，愛分析，較冷靜", 4),
        ],
    },
    {
        "id": "HUM10",
        "text": "在每一次會議中或公司決策提案時，你所扮演的角色為何：",
        "options": [
            ("據理力爭者", 1),
            ("協調者", 2),
            ("贊同多數者", 3),
            ("分析所有提案以供參考者", 4),
        ],
    },
    {
        "id": "HUM11",
        "text": "依照直覺選一個：",
        "options": [
            ("我做事一向以具體、短期能達到目標；決定快速，立即得到結果", 1),
            ("在本性上，我喜歡跟人交往，各式各樣的人甚至陌生人都行", 2),
            ("我不喜歡強出頭，寧可當後補", 3),
            ("我是一個自我約束、很守紀律的人，凡事依既定目標行事", 4),
        ],
    },
    {
        "id": "HUM12",
        "text": "依照直覺選一個：",
        "options": [
            ("我喜歡有變化、激烈且競爭的環境，是個可接受挑戰的人", 1),
            ("我喜歡社交，也喜歡招待人", 2),
            ("我喜歡成為小組的一份子，固守一般性程序", 3),
            ("我會花很多時間去研究事與人", 4),
        ],
    },
    {
        "id": "HUM13",
        "text": "依照直覺選一個：",
        "options": [
            ("我喜歡按自己的方法做事，不在乎別人對我的觀感，只要成功", 1),
            ("有人跟我意見不一致時，我會很困擾", 2),
            ("我知道改變有必要，但還是覺得少冒險比較好", 3),
            ("我對自己及他人的期望很高，這些都是為符合我的高標準", 4),
        ],
    },
    {
        "id": "HUM14",
        "text": "依照直覺選一個：",
        "options": [
            ("我擅長處理棘手的問題", 1),
            ("我是個很熱心的人，我喜歡跟別人一起工作", 2),
            ("我喜歡聽而不喜歡說話，一開口都說得很委婉溫和", 3),
            ("處理事情我較不動感情，是就是，不把感情牽扯進來，也較少與人閒聊", 4),
        ],
    },
    {
        "id": "HUM15",
        "text": "依照直覺選一個：",
        "options": [
            ("我喜歡有競爭，有競爭才能把潛能完全發揮出來", 1),
            ("我較感性，與人相處或處事較不注意細節", 2),
            ("我是個理性的組員，順著群眾，具有高度的團體意識", 3),
            ("對事我喜歡去研究，講求證據與保證", 4),
        ],
    },
    {
        "id": "HUM16",
        "text": "依照直覺選一個：",
        "options": [
            ("我喜歡能力與權威，這是我想要的", 1),
            ("我有時情緒化；置身有趣事務時，也可能無法掌握時間", 2),
            ("我喜歡按部就班、穩紮穩打，不喜歡孤注一擲的方式", 3),
            ("我很注意事務與人的細節", 4),
        ],
    },
    {
        "id": "HUM17",
        "text": "依照直覺選一個：",
        "options": [
            ("對直接關係的環境，我有喜歡掌握及支配他人的傾向", 1),
            ("在團體中我喜歡打成一片，活潑、有氣氛、有感情地相處", 2),
            ("我較遵守傳統步驟做事，不喜歡有很大的變化", 3),
            ("在掌握事實真相與更多資料之前，我寧可保持現狀", 4),
        ],
    },
    {
        "id": "HUM18",
        "text": "依照直覺選一個：",
        "options": [
            ("我與人溝通時會直接了當地說，不喜歡兜圈子", 1),
            ("我喜歡幫助人，相親相愛", 2),
            ("我不喜歡多變化的環境，而要穩定安全的生活方式", 3),
            ("凡事我要求準確無誤，講求高品質、高標準的處事原則", 4),
        ],
    },
    {
        "id": "HUM19",
        "text": "依照直覺選一個：",
        "options": [
            ("我不喜歡別人逗我開心，不喜歡太多話的人", 1),
            ("我喜歡參加團體活動，因為與很多人在一起感覺很好", 2),
            ("對事情我沒有太多要求與意見，喜歡靜靜、有耐心地做", 3),
            ("我做事要有一套經過計畫設計的標準作業程序來引導方向", 4),
        ],
    },
    {
        "id": "HUM20",
        "text": "依照直覺選一個：",
        "options": [
            ("我討厭別人告訴我事情該如何做，因我自有定見，不喜歡被支配", 1),
            ("我是個生氣勃勃外向的人，能激起一起工作者的熱心", 2),
            ("我喜歡獨處；若與人生活在一起，會盡量不打擾他人", 3),
            ("我很少加入閒聊；話題有趣時，會找更多資料並小心進行", 4),
        ],
    },
]


def calculate_life_path(year: int, month: int, day: int) -> int:
    """Validate a full Gregorian birth date and reduce all digits to 1–9."""
    year = int(year)
    month = int(month)
    day = int(day)
    date(year, month, day)

    value = sum(int(char) for char in f"{year:04d}{month:02d}{day:02d}")
    while value > 9:
        value = sum(int(char) for char in str(value))
    return value


def _combined_animal_profile(dominant_values: list[int]) -> Dict[str, str]:
    profiles = [ANIMAL_PROFILES[value] for value in dominant_values]
    if len(profiles) == 1:
        return dict(profiles[0])
    return {
        "summary": "你的外在風格會在兩種主型之間自然切換："
        + "；".join(profile["summary"] for profile in profiles),
        "team_strength": "同時擁有"
        + "，也能".join(profile["team_strength"] for profile in profiles),
        "blind_spot": "雙主型讓你更有彈性，也要留意角色切換過快："
        + "；".join(profile["blind_spot"] for profile in profiles),
        "collaboration": "和你合作時，可同時參考兩種方式："
        + "；".join(profile["collaboration"] for profile in profiles),
        "action": profiles[0]["action"],
    }


def compute_humanity_report(
    answers: Mapping[int, Any],
    life_path: int,
) -> Dict[str, Any]:
    """Return a presentation-ready report without retaining the raw birth date."""
    life_path = int(life_path)
    if life_path not in LIFE_PATH_PROFILES:
        raise ValueError("life_path must be between 1 and 9")

    values = []
    for number, _question in enumerate(HUMANITY_QUESTIONS, start=1):
        if number not in answers:
            raise ValueError(f"missing answer {number}")
        value = int(answers[number])
        if value not in ANIMAL_ORDER:
            raise ValueError(f"invalid answer {number}")
        values.append(value)

    counts = Counter(values)
    score_by_value = {value: int(counts.get(value, 0)) for value in ANIMAL_ORDER}
    max_score = max(score_by_value.values())

    if max_score < 7:
        dominant_values: list[int] = []
        animal_profile = dict(ANIMAL_PROFILES["octopus"])
        animal_title = animal_profile["label"]
        animal_emoji = animal_profile["emoji"]
        intensity = "balanced"
        primary = "octopus"
        secondary = ""
        is_mixed = False
    else:
        dominant_values = [
            value for value in ANIMAL_ORDER if score_by_value[value] == max_score
        ]
        is_mixed = len(dominant_values) > 1
        prefix = "大" if max_score > 7 else ""
        animal_title = " × ".join(
            f"{prefix}{ANIMAL_PROFILES[value]['label']}"
            for value in dominant_values
        )
        animal_emoji = "".join(
            ANIMAL_PROFILES[value]["emoji"] for value in dominant_values
        )
        animal_profile = _combined_animal_profile(dominant_values)
        intensity = "big" if max_score > 7 else "standard"
        primary = ANIMAL_PROFILES[dominant_values[0]]["code"]
        secondary = (
            ANIMAL_PROFILES[dominant_values[1]]["code"] if is_mixed else ""
        )

    core = LIFE_PATH_PROFILES[life_path]
    scores = {
        ANIMAL_PROFILES[value]["label"]: score_by_value[value]
        for value in ANIMAL_ORDER
    }
    primary_label = animal_title
    secondary_label = (
        ANIMAL_PROFILES[dominant_values[1]]["label"]
        if len(dominant_values) > 1
        else ""
    )

    return {
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
        "combined_title": f"{life_path}號{core['label']} × {animal_title}",
        "summary": f"{core['essence']}外在與團隊互動則呈現「{animal_title}」：{animal_profile['summary']}",
        "strengths": [*core["strengths"], animal_profile["team_strength"]],
        "team_strength": animal_profile["team_strength"],
        "blind_spot": f"{core['blind_spot']}{animal_profile['blind_spot']}",
        "collaboration": animal_profile["collaboration"],
        "next_action": animal_profile["action"],
        "counts": scores,
        "scores": scores,
    }
