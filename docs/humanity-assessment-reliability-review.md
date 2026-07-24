# 人性探索 20 題：精準度與可靠性研究

研究日期：2026-07-24
目的：評估目前「老虎、海豚、企鵝、蜜蜂／八爪」20 題測驗能否宣稱精準可靠，並提出適合數位名片的改版方向。

## 結論

目前網路版與本專案的測驗適合當作低門檻的自我探索與團隊對話工具，但尚不足以宣稱為經過驗證的精準人格測驗。

主要原因：

1. 每題四選一，而且四類總分固定合計為 20，屬於傳統強迫選擇的零和計分。一個分數上升，其他分數必然下降，無法表達同一個人可能同時具有多項強烈特質。
2. 用最高票直接決定動物類型，接近分數可能因一題而翻轉，現有計分沒有信賴區間、分類穩定度或代表性常模。
3. 將選項打散只能降低位置與作答慣性偏誤，不能建立信度或效度。
4. 四動物概念與 DiSC 類似，但免費 20 題並不是 Wiley 的 Everything DiSC；不能把商業版 DiSC 的研究證據直接移植到目前題目。

若「20 題、容易完成、又希望更可靠」是優先條件，最合適的做法是用公開領域的 Mini-IPIP 20 題作為測量核心，以五點量尺分別計算 Big Five 五個連續向度；動物名稱只保留為結果頁的故事化包裝。

## 現有測驗的結構問題

目前題目每題都對應：

- 老虎：主導、行動、決斷
- 海豚：外向、影響、表達
- 企鵝：穩定、支持、合作
- 蜜蜂：分析、規範、精確

四類計數加總永遠等於 20。傳統強迫選擇計分會形成 ipsative data。相關研究指出，這種分數不適合直接拿來做人與人之間的比較，也會扭曲量尺間相關、信度與效標效度；若一定要採強迫選擇，需要以 Thurstonian IRT 等模型重新設計與估計，而不是只計票。

來源：

- Brown, A., & Maydeu-Olivares, A. (2011). [How IRT Can Solve Problems of Ipsative Data in Forced-Choice Questionnaires](https://eric.ed.gov/?id=EJ1004409)
- Schulte et al. (2023). [Can High-Dimensional Questionnaires Resolve the Ipsativity Issue of Forced-Choice Response Formats?](https://pmc.ncbi.nlm.nih.gov/articles/PMC10621689/)

## 網路框架比較

| 方案 | 優點 | 限制 | 適合本專案 |
|---|---|---|---|
| 現有四動物 20 題 | 有趣、直覺、完成快 | 未找到此題組的正式信效度；零和計票；分類容易翻轉 | 可作趣味探索，不宜宣稱精準診斷 |
| Everything DiSC | 有商業版技術手冊、重測與建構效度證據 | 專有授權；不能把證據移植到自編動物題 | 若願意購買正式授權才考慮 |
| Mini-IPIP 20 題 | 正好 20 題；公開領域；五因素結構；有跨研究與中文版證據 | 台灣繁中版仍需本地化與試測；每向度只有四題，精細度有限 | 最推薦作為測量核心 |
| BFI-2-S / BFI-2-XS | Big Five 架構成熟 | 分別為 30 題／15 題；授權與使用條件需確認 | 可作外部效度比較或替代方案 |

Everything DiSC 技術報告提供其自有量表的信度、重測與建構效度資料，但該證據僅適用於其題目、計分與常模：

- [Everything DiSC Research Report](https://www.discprofile.com/CMS/media/doc/ed/research/research-report.pdf)
- [Everything DiSC Manual](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/everything-disc-manual-978-1-119-08067-1)

## 建議的 20 題核心

Mini-IPIP 以 20 題測量：

1. 外向性
2. 親和性
3. 盡責性
4. 情緒穩定／神經質
5. 開放性／想像力

每個向度四題，使用「非常不像我」至「非常像我」的五點量尺，並包含正向題與反向題。原始研究在五項研究中檢查內部一致性、重測、收斂、區辨與效標關聯。官方 IPIP 題庫為公開領域，可複製、翻譯與調整。

來源：

- Donnellan et al. (2006). [The Mini-IPIP Scales](https://doi.org/10.1037/1040-3590.18.2.192)
- [International Personality Item Pool](https://ipip.ori.org/)

一項中國樣本研究（N=1,563）支持 Mini-IPIP 的五因素結構，報告 Cronbach's alpha 約 .79–.84、McDonald's omega 約 .73–.82，並附有簡體中文翻譯。不過樣本為中國地震倖存者，不能直接視為台灣一般社群使用者的常模。

- Li et al. (2012). [The Mini-IPIP Scale: Psychometric Features and Relations with PTSD Symptoms of Chinese Earthquake Survivors](https://ir.psych.ac.cn/bitstream/311026/13300/11/WOS000311007600027.pdf)

## 適合數位名片的呈現

建議前台使用：

> 20 題團隊互動探索
> 看見你在互動、行動、合作、規劃與適應上的自然傾向。

結果不要只給一個「你是某動物」，而應顯示：

- 五個連續向度
- 最明顯的兩項傾向
- 可能優勢
- 壓力下的盲點
- 別人和你合作的建議
- 「你的團隊風格故事最接近：主型＋副型」

動物可作故事層，例如「老虎 × 蜜蜂」，但需要明示它是依五項特質產生的溝通風格摘要，而非臨床診斷或固定人格。

目前宣稱「你在團隊裡怎麼被看見」也偏強，因為單純自評只能反映自己如何看自己。若要支持此說法，應加入同事／夥伴的觀察版本；否則改成「你自認的團隊互動傾向」較準確。

生命靈數不能併入心理量表總分。可以放在同一頁作趣味對照，但要分開說明資料來源與用途。

## 最低驗證計畫

1. 使用 Mini-IPIP 原始構念與正反向結構，完成繁中翻譯、回譯。
2. 找 10–20 位台灣目標使用者做認知訪談，確認每題讀法一致。
3. 以至少約 100 人做初步試測，檢查完成率、作答分布與各向度 alpha／omega。
4. 以約 300 名目標族群做五因素驗證性因素分析，並和已建立量表或夥伴評分比較。
5. 另找 50–100 人於 2–4 週後重測，檢查分數與故事分類是否穩定。
6. 未有代表性台灣樣本前，不顯示常模百分位，也不使用「精準診斷」。
7. 公開一頁簡短技術說明：版本、題目來源、計分、樣本、信度、效度與限制。

測驗翻譯與本地化後，原量表的信效度不會自動轉移。國際測驗委員會要求重新蒐集內容、反應歷程、內部結構、外部關聯與使用後果的證據：

- [International Test Commission Guidelines for Translating and Adapting Tests](https://www.intestcom.org/files/guideline_test_adaptation_2ed.pdf)
- [Standards for Educational and Psychological Testing](https://www.apa.org/science/programs/testing/standards)

## 建議決策

優先採用：

**Mini-IPIP 20 題五點量尺 → 五向度連續分數 → 主傾向＋次傾向 → 動物故事化呈現。**

這能保留目前動物介面的親切感，也比「每題選一個、最高票決定類型」更能支持精準、可解釋且可逐步驗證的結果。
