# RICH 成長漏斗 v2.1

## 已完成

- 事件追蹤：來源、活動、入口、測驗、題目進度、完成、結果、同意建立名單、分享包。
- 三種入口：`friend`、`cold`、`social`，並支援 `src`、`campaign`、`quiz`。
- 結果不設門檻：完整解析先顯示，興趣與 LINE 都是選填。
- 明確同意：只有按下「同意儲存結果並通知分享夥伴」才寫入 `leads`。
- 夥伴分享包：LINE、Instagram、Facebook，以及結果後的跟進文字。
- 測驗品質：移除人工等待；題目不再預選第一個答案。
- 安全清理：移除全域停用 TLS 驗證，並將 `.venv/`、`.env`、Secrets、備份檔加入忽略規則。
- 安全驗收：新增 `RICH_DEMO_MODE=1`，不連 Google Sheet、不送 LINE、不寫事件。
- 視覺驗收：修正 Demo 徽章破圖、Material Icon 顯示成文字、手機首屏看不到開始 CTA。
- 手機轉換：將稱呼與狀態改為折疊式選填區，主要 CTA 可在首屏直接看到。
- 主打測驗：新增「生日能量 × 行動性格」，以月日推導 1–9 號核心，再用 10 題行動題產生五向風格與組合原型。
- 生日隱私：不要求出生年份；原始月日不寫入事件、名單或分享文字，只使用推導後的核心號碼。
- 測驗編排：生日主測驗放在首頁，原財富與健康測驗保留於「更多探索」。
- 手機 CTA：首頁在手機底部固定顯示開始按鈕，進入答題後自動消失。

## 新增檔案

- `growth_features.py`：入口文案、追蹤資料與分享包純函式。
- `birthday_profile.py`：生日核心、10 題行動題與五向風格純計分函式。
- `test_birthday_profile.py`：生日日期驗證、正反向計分與隱私欄位測試。
- `test_growth_features.py`：入口、事件與分享連結單元測試。
- `test_streamlit_demo.py`：三種入口、答題、完整結果、分享包與安全留單流程測試。
- `events_header.csv`：事件工作表欄位。
- `DEPLOYMENT.md`：部署與測試說明。
- `SECURITY.md`：KEY 與資料安全注意事項。

## 部署前必做

1. 新增 Google Sheet 工作表 `events`，貼上 `events_header.csv` 第一列。
2. Streamlit Secrets 設定 `ENABLE_EVENT_TRACKING = true`。
3. 先以測試用 Sheet 驗證，不要直接對正式名單測試。
4. 不要上傳原始 ZIP 中的 `.venv/`。
