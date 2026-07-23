# 安全檢查摘要

此版本不包含 `.env`、Streamlit Secrets、Google service account 私鑰或硬編碼 API KEY。

部署與分享時：

1. 不要提交 `.venv/`、`.streamlit/secrets.toml`、`.env` 或 service account JSON。
2. LINE access token 應放在 Streamlit Secrets，不要放在可分享的 Google Sheet。
3. 管理密碼不要使用明碼工作表欄位；後續應改為雜湊驗證或正式登入。
4. Google Sheet 必須限制為必要帳號存取，不要設定「知道連結即可查看」。
5. 若任何 token 曾出現在公開 Sheet、GitHub commit 或聊天截圖中，應立即撤銷並重新產生。
6. `app.py.bak` 僅供原始版本比對，不應部署或重新提交。
7. 視覺驗收可設定本機環境變數 `RICH_DEMO_MODE=1`；此模式使用假夥伴資料，並停用 Google Sheet、LINE 與事件寫入。

原始 ZIP 內含完整 `.venv`，其中會有本機絕對路徑與第三方套件測試憑證；它們不是此專案的 API KEY，但應從所有交付包移除。
