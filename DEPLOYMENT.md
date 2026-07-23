# RICH 成長漏斗 v2 部署說明

## 1. 建立事件工作表

在目前的 Google Spreadsheet 新增工作表，名稱必須是：

```text
events
```

第一列依序貼上以下欄位：

```text
time	session_id	event	ref_input	ref_resolved	partner_name	source	campaign	entry	quiz_id	step	lead_id	meta
```

事件表只記錄漏斗資訊。訪客未主動同意建立名單前，不會把稱呼寫進事件表。

## 2. 啟用事件追蹤

在 Streamlit Secrets 增加：

```toml
ENABLE_EVENT_TRACKING = true
APP_PUBLIC_URL = "https://richaiproject-xzwznzb6fdd35n8otuxgha.streamlit.app/"
ENABLE_LEGACY_ADMIN_PANEL = false
```

未建立 `events` 工作表前，請保持 `ENABLE_EVENT_TRACKING = false`，避免事件寫入失敗。

原有 Google Sheets 與 LINE secrets 保持在 Streamlit Secrets；不要放進 GitHub、ZIP 或工作表公開欄位。

舊版管理面板使用工作表明碼密碼，因此新版預設停用。未改成正式登入或雜湊驗證前，不建議設定為 `true`。

## 3. 三種入口

### 夥伴朋友

```text
?ref=ting&src=line&campaign=friend01&entry=friend&quiz=wealth
```

### 陌生開發

```text
?ref=master&src=fb&campaign=cold01&entry=cold&quiz=wealth
```

### 社群入口

```text
?ref=vera&src=ig&campaign=health01&entry=social&quiz=health
```

參數：

- `ref`：夥伴代碼。
- `src`：`line`、`ig`、`fb`、`qr` 等來源。
- `campaign`：活動代碼，建議使用短英文與數字。
- `entry`：`friend`、`cold`、`social`。
- `quiz`：`wealth` 或 `health`。省略時讓訪客自行選擇。

## 4. 事件定義

- `page_opened`：開啟網站。
- `intro_viewed`：看到入口首頁。
- `quiz_selected`：自行選擇測驗。
- `quiz_started`：開始答題。
- `quiz_step_viewed`：看到某一題。
- `quiz_completed`：完成全部題目。
- `result_viewed`：看到完整結果。
- `interest_opted_in`：同意儲存興趣。
- `lead_saved`：名單成功寫入。
- `line_cta_shown`：結果頁顯示 LINE 行動按鈕。
- `share_pack_viewed`：看到結果分享包。

可用 `session_id` 串起同一位匿名訪客的事件。公開前期不要以稱呼作為漏斗識別碼。

## 5. 本機安全預覽

若只想驗收畫面、不讀寫正式 Google Sheet、不送 LINE、不記錄事件，可用：

```bash
RICH_DEMO_MODE=1 streamlit run app.py --server.address=127.0.0.1 --server.port=8501
```

再開啟：

```text
http://127.0.0.1:8501/?ref=master&src=line&campaign=qa&entry=friend&quiz=wealth
```

`RICH_DEMO_MODE` 只從本機環境變數讀取，不能透過公開網址參數開啟。

## 6. 驗證

```bash
python3 -m py_compile app.py growth_features.py
RICH_DEMO_MODE=1 python3 -m unittest discover -v
streamlit run app.py
```

建議先使用測試用 Spreadsheet 副本確認事件與名單，再切換正式 Spreadsheet。
