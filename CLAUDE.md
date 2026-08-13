# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SOC_RESEARCH is a research project focused on **battery State-of-Charge (SOC) and State-of-Health (SOH) estimation methods**. The research covers lead-acid batteries, lithium-ion batteries, Kalman filtering, neural network approaches, and LFP battery hysteresis modeling.

The project is transitioning from a pure documentation/literature review phase into MCU firmware implementation.

## Repository Structure

- **DOC/** — All research documentation, organized into:
  - `參考論文/` — Original reference papers (PDF), 3 papers covering lead-acid SoH/SoC, lithium-ion SOC/SOH, and multilayer neural network methods
  - `論文簡報/` — Chinese and English summaries of the reference papers (DOCX)
  - `會議紀錄/` — Meeting presentations (PPTX) named as `meeting_MMDD_洪大甲`, plus related materials
  - `主題簡報/` — Topic-specific presentations on SOC/Kalman filter concepts and LFP hysteresis modeling
  - `校正紀錄/` — Instrument calibration logs (INA226 multi-point LUT etc.)
  - `論文撰寫/` — Thesis outline + official templates (`論文大綱.md` is source of truth)
  - `分析紀錄/` — **Self-contained analysis reports on test data**. Each report is dated and points to source CSVs; new conversations should read these to resume context. Currently: `2026-05-18_rate_capability_and_R_analysis.md`
- **TEST/** — Bench automation: round_runner, GITT runner, drivers (IT6302/IT8512/INA226), and `data/` containing per-cycle CSV traces + `cycle_log.csv` aggregate metadata
- **MCU/** — Reserved for embedded firmware code (currently empty, pending implementation)

## Research Topics

- Lead-acid battery SoH/SoC measurement design and implementation
- Lithium-ion battery SOC/SOH estimation techniques
- Multilayer neural network-based SOC estimation and SOH diagnosis
- Kalman filter for SOC estimation
- LFP battery hysteresis modeling and SOC compensation

## Conventions

- File naming for meetings: `meeting_MMDD_洪大甲` format
- All documentation and communication in **Traditional Chinese (繁體中文)**
- When MCU code is added, follow MISRA C standards (see global CLAUDE.md for detailed C coding rules)

---

## 今日總結

### 2026/08/13（論文精華海報：A4 直式單頁，DOCX＋PDF；同日第二段工作）

#### ✅ 完成項目
- **新建 `DOC/論文精華海報/`，產出 A4 直式單頁海報**（`論文精華海報_A4.docx` ＋ PDF）：內容全部取自論文六章實測結果，既有論文與研討會論文檔案完全未動
- **版面結構**：標題區（跨頁寬，中英題目＋作者＋深藍亮點條）→ 雙欄主體（以 1×2 表格佈局；左欄：研究動機／測試平台＋圖 1／三法嵌入式實作；右欄：強健性壓力測試表／核心發現＋圖 2）→ 跨欄底部（圖 3 三法軌跡／精度—資源—適用情境總表／結論框）
- **三張圖以 1:1 列印尺寸重繪**（`figures/_gen_poster_figs.py`），非縮放論文原圖：欄內圖寬 3.35 吋、跨欄 7.09 吋，圖內字級 5.6–7.0 pt，確保列印後可讀
- **圖 3 的 RMSE 由原始資料重算**（Round 41 CSV ＋ `mcu_soc_log_20260707_210836.log`）：1.0C 庫倫 1.77%／EKF 0.22%／阻抗 23.1%，2.0C 1.74%／0.79%／28.0%，與論文表 4-4 完全一致＝管線交叉驗證
- **內容取捨**：原精度表（表 4-4）與資源表（表 4-6）分列必定超一頁，改成跨欄一張「精度─資源─適用情境」總表（併入第六章決策表資訊），一眼看完三法權衡，正好對應論文核心命題「精度─成本權衡」
- 依使用者要求移除指導教授「博士」頭銜後重出 docx＋PDF

#### 🐛 問題與踩坑
- **單頁是硬約束，需迭代收斂**：首版 3 頁 → 2 頁 → 1 頁共五輪。有效手段依序為：合併兩張表為一張跨欄總表（省最多，約 230 pt）、精簡 bullet 文字、縮圖寬、降字級與段距
- **Word 文件結尾必有一個段落**：內容已排到 y=812 pt（可用底線 824.9）卻仍分兩頁，真因是結尾表格之後 Word 自動生成的 Normal 段落（7.4 pt ≈ 10 pt 高）塞不下。修法：明確追加一個空段落並把 `line_spacing` 設為 `Pt(1)`（精確行高 1 pt）
- **相鄰表格會被 Word 併成同一個表格**：亮點條、雙欄主體、結論框都是表格，之間必須插 1 pt 空段落分隔
- **版面留白必須量測，不能目視估**：每輪用 PyMuPDF `page.get_text('blocks')` 量內容最大 y 對照可用底線，才知道還差幾 pt；目視只看得出「有沒有溢頁」，無法量化該砍多少字
- **孤字要逐條修**：段落末行只剩「加。」「程。」「擇。」等 1–2 字很醜，需逐句刪 2–4 字讓它縮回前一行
- **matplotlib 圖字級要按最終列印尺寸反推**：論文圖原以 8.2×6.2 吋、字 11 pt 繪製，縮到欄寬 8.5 cm 後字僅剩 4.3 pt 不可讀；重繪時 figsize 直接設成列印尺寸
- **方塊圖行距要隨 figsize 等比縮**：架構圖沿用原座標系但 figsize 砍半後，兩行文字幾乎黏在一起、長標籤溢出方塊；需同步調行距（0.36→0.52 座標單位）、加寬方塊、降字級，產完必 Read PNG 目視
- **Microsoft JhengHei 缺 U+2248（≈）**：`量測域差 ≈ 24 mΩ` 渲染成方框，改用「約」

#### 📋 待辦
- 海報作者列的姓名（洪大甲）與系所（資訊工程學系碩士班）取自專案既有紀錄，論文封面該兩項原為佔位，正式輸出前請核對
- 論文既有待辦延續（封面姓名／指導教授佔位、方程式編輯器重排、圖 3-3 測試照片補入後重匯 PDF、13 篇付費文獻待圖書館下載）

### 2026/08/13（研討會投稿論文 _2026081002：表 I 移到跨欄圖之後，消除頁 3 右上大片空白）

#### ✅ 完成項目
- **產出 `_2026081002` 版**（`DOC/研討會報告/`，docx＋PDF，4 頁；`_20260810` 與 `_20260722` 兩版時間戳未變、完全未動）：把 **Table I 從跨欄 Figure 2 之前移到之後**
- **解決的問題**：原版頁 3 頂端只有 Table I 佔左欄，**右上約 8.9 × 12 cm 全空**。成因是該段雙欄區裡只剩一張表，Word 的欄平衡把它全塞進左欄、右欄自然空掉。把跨欄圖提到前面後，頁 3 頂端變成滿版的 Figure 2，Table I 落到圖下方雙欄區且右欄有 4.2 節內文接續
- 量測驗證：頁 3 右欄起始由 y=563 pt 提前到 y=452 pt；四頁的欄底留白分別為 0.06／0.22／0.26／6.93 cm，無異常
- **順手改良 `add_figure(span=True)` 的分節實作**：原本會先造一個 spacer 空段落來掛 2 欄 `sectPr`；移動後跨欄圖緊接內文，該 spacer 會在頁 2 底部留下多餘空行。改成直接把 `sectPr` 掛在**前一個內文段落**上，並加保護——前一個元素若是表格就退回用 spacer
- 驗證與舊版逐項一致：4 頁、無中文摘要殘留、無 NMC、[1]–[11] 全部有內文引用、`TABLE I/II/III` 與 `Figure 1/2` 編號與所在頁均正確

#### 🐛 問題與踩坑
- **`sectPr` 掛錯位置會把表格推進錯的節**：段落的 `sectPr` 定義的是「結束於該段落的那一節」，若前一個元素是表格而把 `sectPr` 掛到表格的標題段上，表格本身會被排除在該節之外。故 `_last["par"]` 在 `add_table()` 結束時必須重設為 `None`
- **Word 雙欄的欄平衡是這類空白的通因**：不可分割的浮動體（表格、圖）若獨占一段雙欄區，Word 會把它擠在左欄、右欄留空。解法是讓該雙欄區「不要只有一個浮動體」——把跨欄圖移到它前面，或讓後續內文能流進來
- **本機 `git status` 顯示的 `??` 不等於會被 commit，但也不等於被 ignore**：`git check-ignore -v` 對 `DOC/離校程序/` 回報命中 `.gitignore:29`，實際上第 29 行是註解 `# Office 暫存鎖檔`、pattern 欄位是空的，屬誤導輸出。**權威判斷要用 `git add -A --dry-run`**，它明確列出那 10 份離校文件都會被收進來

- **`DOC/離校程序/` 10 份個人行政文件一併納入版控**：該資料夾未被 .gitignore 排除，而本 repo 為 public，已就「推上去不可逆、即使刪除仍可能被快取或索引」提出說明，**使用者確認照常提交上傳**
- **`my-claude-extensions` repo 分岔已解**：本機 85ebcf7（stm32-build-flash）與遠端 bf9493e（auto-git-commit）改不同檔案，以 `merge --no-ff` 併入（a57f96a）後推送，兩邊內容均保留
- **經驗回寫 `auto-git-commit` skill**（commit be2c71c）：新增「`git check-ignore` 輸出會誤導、判斷 `add -A` 實際範圍只能用 `--dry-run`、public repo 遇個人文件要先查可見性並交回使用者決定」一條，作為硬規則「一律 add -A 不挑檔」的邊界保護

#### 📋 待辦
- 研討會論文既有待辦延續（表格標題 tab 空隙、作者英文拼音、內文「(Table I); Fig. 2」引用順序與版面實體順序相反，IEEE 合規但可調）

### 2026/08/10（研討會投稿論文 _20260810：改以 TANET 官方範本為基底重建、移除中文摘要、文獻去 arXiv）

#### ✅ 完成項目
- **產出研討會投稿論文 `_20260810` 版**（`DOC/研討會報告/`，docx＋PDF，4 頁；原 `_20260722` 版與其 PDF 完全未動）：依使用者提供的 `refer/TANET_Format_Paper.docx`（IEEE 版式的 TANET 中文化範本）重建
- **不是「改舊檔套新格式」，而是直接以範本為基底**：載入範本後保留其 `styles.xml`／`numbering.xml`／分節幾何，清空範例內容再把論文內容填回去，因此行高、間距、縮排、字級全部由範本具名樣式決定，非手寫近似值
- **逆向抽出範本完整規格並照用**：A4、上 1.91／下 4.29／左右 1.29 cm；雙欄各 5040 twips、欄距 360；本文 `本文1` 10 pt／行高 228 auto（0.95 倍）／段後 6 pt／首行縮排 288 twips／兩端對齊／字距 −0.05 pt；`Abstract` 粗體 9 pt；`key words` 粗斜體 9 pt；`references` 8 pt／行高 180 exact
- **中文摘要與中文關鍵詞全部移除**（範本本身即只有英文 Abstract），PDF 抽字驗證 `摘要`／`關鍵詞`／`鋰離子` 皆 0 次
- **章節／表／圖／文獻編號全改為範本的 Word 自動編號欄位**：`標題 11` 自動羅馬數字＋小型大寫置中、`標題 21` 自動 A./B. 斜體靠左、`table head` 自動「TABLE I.」、`figure caption` 自動「Figure 1.」、`references` 自動「[1]」，在 Word 內增刪會自行重編
- 內文交叉引用同步改 `Table I／II／III`、`Section I`；三條顯示方程式改 IEEE 慣例的置中＋右靠編號 (1)(2)(3) 並在內文引用
- **11 篇參考文獻全部由 arXiv 預印本換成正式出處**（沿用論文 `_20260803` 版成果）：IECON／IEEE CCTA／IEEE ESL／Energies／IJRER／IEEE VPPC／ACC／J. Energy Storage／Sci. Rep./IEEE TII／IEEE TTE；驗證 [1]–[11] 全部有內文引用、零孤兒文獻
- **修掉與 2026/08/03「全論文移除 NMC」不一致的殘留**：圖 1 方塊原寫 `NMC 2000 mAh` 改 `Li-ion 2000 mAh`（改 `figures/gen_fig_arch_en.py` 並重產 PNG），內文同步改「custom lithium-ion unit」
- 逐頁 PDF 目視＋PyMuPDF 量測驗證；跨欄圖 2 正常橫跨整頁寬，分節結構為 5 節（標題單欄→雙欄→跨欄圖單欄→雙欄→尾段單欄）
- 討論「研討會參考文獻是否要比照主論文 33 篇」：結論不需要，4 頁短篇 11 篇屬正常區間，硬補會產生孤兒文獻；已指出三處引用斷點（GITT 無出處、缺 Plett 2004 電池 EKF 奠基文獻、ECM 論述誤掛在 Zhao 靈敏度分析上）並建議補 3 篇成 14 篇，**使用者決定維持 11 篇不動**

#### 🐛 問題與踩坑
- **python-docx 沒有「插入到指定位置」API**：`doc.add_paragraph()` 一律落在 body 末端 sectPr 之前。修法是先 `add_paragraph()` 再用 `anchor.addprevious(par._p)` 把 XML 元素搬到目標錨點前，表格同理搬 `t._tbl`
- **sectPr 語意方向容易搞反**：段落的 `sectPr` 定義的是「**結束於**該段落的那一節」，不是其後那節。跨欄圖因此實作成「圖前的最後一段掛 2 欄 sectPr、圖說段掛 1 欄 sectPr」，比 `add_section()` 少產生兩個多餘空段落
- **範本 `equation` 樣式的 run 字型是 Symbol**：直接打字整行會變希臘字母亂碼，必須在 run 層覆寫 `w:rFonts` 四個屬性（ascii／hAnsi／cs／eastAsia）為 Times New Roman
- **範本樣式名是 CJK、styleId 卻是數字**（`標題 11`→id `11`、`內文1`→id `1`、`本文1`→id `13`），python-docx 的 `p.style = ...` 要用 **name** 不是 id，讀 styles.xml 時兩者都要印出來對照
- **`element.itertext()` 會讀到重複文字**（範本 run 結構特殊），驗證段落內容要用 `paragraph.text`（只收 `w:r/w:t` 直屬子項）
- **版面留白不能目視估**：目視以為頁 2 右欄缺約 4 cm，改用 PyMuPDF 逐頁量 block bbox 對文字區下緣，實測只有 1.45 cm，屬雙欄排版常態，白改一輪版面
- **範本刪除範例內容後圖片關聯會變孤兒**：先掃 `a:blip` 收 rId 再 `doc.part.drop_rel(rId)`，才不會留 24 KB 未引用的 image1.png
- **`git push` 連續失敗，真因是公司兩台 proxy 走錯（當日稍晚排查）**：git 報 `schannel: server closed abruptly (missing close_notify)`，實際上是代理回 **403 Forbidden** 加 `Connection: close` 後把 TLS 連線硬關，schannel 訊息只是表象。公司系統代理是 `rdproxy`（瀏覽器／PowerShell 走這台、通），但 `HTTP_PROXY`／`HTTPS_PROXY` 環境變數指向 `fspproxy`（git 走這台、被擋）。改用 `git -c http.proxy=http://rdproxy...:8080 push` 一次就通
- **診斷過程中兩個「假證據」害我先誤判成網路斷線**：`Test-NetConnection` 回 False 是被工具沙箱擋；`curl.exe` 回 `http=000` 是它用自帶 CA bundle、不信任公司閘道 TLS 攔截用的根憑證（連 example.com 都失敗）。真正定位靠 `GIT_CURL_VERBOSE=1`，一跑就看到 `Proxy-Agent: IWSS` 與 `HTTP/1.1 403 Forbidden`
- **經驗已回寫 `auto-git-commit` skill**（commit c58b666）：新增 `scripts/git-proxy-auto.ps1`（依當下 Windows 系統代理自動帶對的 proxy，家用網路則主動把 `http.proxy` 設空字串蓋掉殘留環境變數）＋ SKILL.md 新增「網路環境切換（公司代理／家用網路）」章節與踩坑筆記。刻意**不設全域 proxy**，因為會在公司與家用網路間切換，設死了回家就連不上

#### 📋 待辦
- 表格標題「TABLE II.」與標題文字間的 tab 空隙為範本 numbering 原生行為（IEEE 官方範本亦如此），若要改成單一空白需調 `w:suff`
- 送印前確認作者英文拼音（現用威妥瑪 Ta-Chia Hung；範本風格可改漢語拼音 Da-Jia Hong）
- 論文既有待辦延續（封面姓名／指導教授佔位、方程式編輯器重排、圖 3-3 測試照片補入後重匯 PDF、13 篇付費文獻待圖書館下載）

### 2026/08/04（參考論文資料夾整理：檔名對齊文獻編號、補下載 7 篇合法公開文獻、建對照清單）

#### ✅ 完成項目
- **參考論文資料夾全面對齊 `_20260803` 版 33 篇參考文獻**：從 docx 抽出完整 [1]–[33] 書目逐篇比對，13 個既有 PDF（3 篇原始參考論文＋10 篇 arXiv 命名）全部以 `git mv` 更名為 `[編號]_第一作者_論文標題.pdf`，檔名可直接對照論文文獻編號
- **刪除不相關檔案**：`State_of_Charge_Estimation_..._Multilayer_Neural_Networks.pdf`（論文自 2026/06/11 已移除資料驅動法／神經網路章節，該文不在 [1]–[33] 內）
- **新下載 7 篇合法公開來源文獻**：[2] Xiong／[4] How（IEEE Access 開放取用）、[10] Chen & Rincon-Mora（Georgia Tech 作者官網自存版）、[14] He（MDPI 開放取用）、[21] Wan & van der Merwe（Harvard SEAS 課程公開託管）、[25] STM32G071 DS12232（DigiKey 託管之 ST 原檔）、[26] INA226 SBOS547A（TI 官網）；每份皆以 pypdf 讀第一頁驗證標題正確
- **建立 `DOC/參考論文/參考文獻對照清單.md`**：33 篇逐條列出來源與取得狀態（已備齊 20／尚缺 13），缺的 13 篇附 DOI 與中原大學圖書館取得路徑（ScienceDirect／IOPscience／ASME／ECS）
- 依使用者要求，論文檔案本身完全未動

#### 🐛 問題與踩坑
- **三個 OA 索引交叉查詢才問得出真相**：Unpaywall 只認出 3 篇、OpenAlex 同源結果一致、Semantic Scholar 多認出 [1] 與 [10]；但 [21] Wan & van der Merwe 三家都判 non-OA，實際上 Harvard SEAS 課程網站有公開 PDF——**索引 API 是起點不是終點，經典文獻仍需針對作者機構做定向搜尋**
- **MDPI `www` 網域被 Akamai 擋 403、`res` 網域直通**：`www.mdpi.com/.../pdf` 帶 Referer 與完整瀏覽器 header 都 403，改用 `res.mdpi.com/energies/energies-04-00582/article_deploy/energies-04-00582.pdf` 一次成功
- **IEEE Access 開放取用全文要走 ielx 路徑**：`stamp.jsp?arnumber=` 只回 HTML frame，`ieeexplore.ieee.org/ielx7/<pubid>/<issueid>/0<arnumber>.pdf` 才是真 PDF
- **cs.unc.edu 的 Kalman 1960 公開託管已下線**（ASME 授權轉錄版，多年來的標準引用來源），實測整頁 404；MIT／CMU 幾個常見鏡像同樣 404，該篇最終無合法免費來源
- **st.com 在本機環境完全不通**（curl 8 分鐘、PowerShell 200 秒皆逾時），Mouser 被 bot 防護擋；最後靠 DigiKey 託管的 ST 原檔取得 DS12232，但只有 Rev 1（2018），論文引用的是 Rev 5（2021）
- **下載後必須驗證 PDF magic 與第一頁文字**：多次收到 301～6000 bytes 的 HTML 偽裝成 `.pdf`（404 頁、Access Denied 頁），`file` 指令加 pypdf 讀首頁是必要關卡

#### 📋 待辦
- 尚缺 13 篇付費文獻（[1][3][6][7][11][15][18][19][20][22][30][31][32]）待以中原大學圖書館電子資源下載，檔名照 `參考文獻對照清單.md` 放入即可對上編號
- [25] STM32G071 datasheet 目前為 DS12232 Rev 1，若要與論文引用一致可自 st.com 下載 Rev 5 覆蓋同名檔
- 論文既有待辦延續（封面姓名／指導教授佔位、方程式編輯器重排、作者英文拼音確認、圖 3-3 測試照片補入後重匯 PDF）

### 2026/08/03（論文 _20260803 進版：新增接線圖／測試流程圖／照片佔位、文獻 13→33 篇去 arXiv、全篇去 NMC、分頁保護）

#### ✅ 完成項目
- **第三章新增兩張正式圖**（原 `_20260722` 不動，另出 `_20260803.docx`）：
  - **圖 3-2 量測迴路接線圖**（`figures/_gen_ch3_wire.py`）：迴路級，粗線功率迴路／細線量測訊號，電池正極經 10 mΩ shunt 分接 IT6302（充）與 IT8512A+（放）兩條互斥路徑，INA226 以 IN+／IN− 跨接 shunt、VBUS 量電池端點，單點共地；標註 Kelvin 四線與軟體互鎖
  - **圖 3-5 跨輪測試協定流程圖**（`figures/_gen_ch3_protocol.py`）：整輪流程（讀回紀錄續接 → CC-CV 充電＋終止判斷迴圈 → 休息 30 分 → 放電含 dV/dI 擾動＋截止判斷迴圈 → 追加跨輪紀錄 → 休息 → k<4 換倍率），右側掛三張說明卡；依使用者要求終點框只留「一輪完成（約 16～18 h）」
- **新增圖 3-3 實際測試照片佔位框**：3.1 節末插 1×1 表格（寬 13.5 cm、列高最小值 9 cm、灰色細框、cantSplit），內含提示文字供使用者貼照片；圖說與引文皆已備妥
- **圖號兩次順移**：韌體骨架 3-2→3-3→**3-4**、測試流程 3-4→**3-5**；內文引用、圖目錄、markdown、圖檔名（`fig3-4.png`／`fig3-5.png`）與繪圖腳本輸出名全部同步
- **參考文獻 13 篇 → 33 篇，且 arXiv 預印本全數換為正式出處**（口委挑「太少」「為何都 arXiv」）：
  - 11 篇 arXiv 逐篇查證改正式書目（Hasan→IEEE CCTA 2018、Song→Energy 193:116732、Qin→IEEE TII 17(11)、Barros→IEEE ESL 17(3)、Movassagh→Energies 14:4074（改用期刊版標題）、Zhao&Howey→IEEE VPPC、Couto→ACC 2018、Kulkarni→J. Energy Storage 91、Knox→Sci. Rep. 14:12472、Baccouche→IJRER 8(1)）
  - 新增 20 篇領域經典（Kalman 1960、Plett EKF 三部曲與 SPKF、Wan&van der Merwe UKF、Hu／He／Chen ECM、Ng 增強庫倫、Roscher LFP OCV、Weppner&Huggins GITT、Waag／Andre 阻抗、Pop／Xiong／Hannan／How 四篇綜述、STM32G071 與 INA226 資料手冊）
  - **編號依首次出現順序重排**（一章 [1]–[9]、二章 [10]–[24]、三章 [25]–[27]、四章 [28]–[32]、五章 [33]），33 篇全部有正文引用、**零孤兒文獻**
- **全論文移除 NMC 字眼**（使用者指正：是 li-ion 非鋰三元）：六章 md、docx、圖 3-1／3-2 圖面、論文大綱、口試簡報、口試講稿；涉及語意處另行改寫（如六章「NMC 的 OCV 曲線平緩」→「該電池的…」）
- **全篇分頁保護**：70 處章節標題設「與下段同頁」、408 段開寡行控制、11 張圖片段落黏住圖說、18 表 98 列設 cantSplit 且末列黏住表標題；實測修掉「2.1.2 內阻模型」標題落頁尾、「3.2 韌體骨架」標題後僅剩一行兩處斷頭
- Word COM 全自動更新三份目錄頁碼，逐頁 PDF 目視驗證後依使用者要求刪除 PDF（使用者手動排版中，補照片後再重匯）

#### 🐛 問題與踩坑
- **Bash heredoc 內字面 `\n` 會被吃掉**：在 `<<'PYEOF'` 中寫 `"\\n"` 期望比對原始碼裡的 `\n` 兩字元，實際傳到 Python 時已成真換行，pattern 全部 miss。修法：用 `chr(92) + 'n'` 拼接，或改用 Edit 工具做這類替換
- **matplotlib 圖插進 docx 會縮到 13.5 cm，字級必須反推**：初版 figsize 9.4×7.2 吋 → 縮放 0.57，9.5 pt 文字實際只有 5.4 pt。改小 figsize 讓字相對放大後，又造成方塊文字溢出框（儀器名稱、頂框長句），必須同步加寬框或降字級，來回兩輪才收斂。**產圖後一律 Read PNG 目視**
- **Microsoft JhengHei 缺 U+2212（MINUS SIGN）**：`IN−`／負極符號渲染警告，改用 ASCII `-`
- **docx 段落定位會誤中目錄快取條目**：`圖 3-2　韌體骨架…` 同時出現在 toc 2 樣式的圖目錄與正文圖說，唯一性斷言直接失敗；`par_by()` 必須排除 `style.name.startswith('toc')`
- **表標題在表格「下方」，keep_with_next 方向設反**：初版把表標題設成黏住下一段內文，實際應是「表格末列黏住其下的表標題」；設錯時表 4-5 標題與表頭仍被頁界切開
- **docx 與 md 有落差**：3.4 節在 md 有「彙整於圖 3-4」引導句、docx 卻沒有（建置腳本漏了對應 EDIT），導致流程圖成為無內文引用的孤兒圖，已補
- **python-docx 存檔會重編 rels**：換圖前擔心誤傷，逐一核對 11 張圖的 rId → media 對應與磁碟檔尺寸後才動手（image1–11 恰依文件順序），確認只換到目標圖

#### 📋 待辦
- 使用者補上圖 3-3 實際測試照片後，重新匯出 PDF（框線可自行設為「無」，仍會約束寬度）
- 文獻書目兩處未取得完整資訊：Yi (2024) IEEE TTE 為 early access 無卷期頁、Baccouche IJRER 僅查到 vol. 8 no. 1 無頁碼，均照現況列出未編造
- 口試簡報／講稿是否比照論文加入接線圖與測試流程圖（本次僅同步 NMC 用語）
- 論文既有待辦延續（封面姓名／指導教授佔位、方程式編輯器重排、作者英文拼音確認）

### 2026/07/27（口試考卷歸檔：新增 DOC/學位考試/）

#### ✅ 完成項目
- **口試考卷文件重整歸檔**：新建 `DOC/學位考試/` 資料夾，收入 `examPaper_11277602.doc`、`examPaper_11277602.pdf`、`exam_11277602.pdf` 三份口試相關文件；原 `DOC/離校手續/exam_11277602.pdf` 移出（該檔改歸於 `學位考試/`）
- 本次為文件歸檔動作，未涉及論文正文、韌體或程式碼變更

#### 📋 待辦
- 論文既有待辦延續（封面姓名/指導教授佔位、方程式編輯器重排、作者英文拼音確認等）

### 2026/07/22（產出 TANET 研討會投稿論文 6 頁 PDF：英文正文＋照實驗室參考論文版面）

#### ✅ 完成項目
- **依使用者實驗室的參考論文版面，產出 6 頁英文投稿論文** 於 `DOC/研討會報告/`（PDF＋同名 docx，檔名用論文英文題目 `A_Comparative_Study_and_Embedded_Implementation_of_SOC_Estimation_Methods_for_Lithium-ion_Batteries`）：A4、**標題區單欄＋正文雙欄**、**中文摘要（標楷體）＋英文 Abstract＋關鍵詞/Keywords**、數字式參考文獻、Times New Roman 10pt／18pt 行距。參考檔為同指導教授（鄭維凱）、同系（資訊工程學系）的 RNN 論文，屬「中文摘要＋英文 Abstract＋英文正文」house style
- **用 PyMuPDF(fitz) 逆向參考 PDF 版面規格**：解析每個 span 的字級/字型/座標，還原標題 16pt bold、節標題 12/11pt bold、雙欄 x 座標（左 70.8pt／右 304.9pt）、18pt exact 行距、圖說 Times bold 10pt 等，再以此複刻
- **python-docx 建構＋Word COM 匯 PDF**：連續分節（WD_SECTION.CONTINUOUS）達成「單欄標題→雙欄正文」；關鍵三法 SOC 軌跡圖以「插入 1 欄分節」跨雙欄置中（IEEE figure* 效果）；win32com ExportAsFixedFormat 出 PDF、fitz 逐頁 render 目視驗證
- **產 2 張英文版圖**（系統架構、三法 SOC 軌跡）：架構圖改寫 matplotlib schematic 英文標籤；SOC 軌跡圖複用本機 Round 41 實測資料（`mcu_soc_log_20260707_210836.log`＋`round041_cyc189–192` CSV）重繪，RMSE 與論文完全一致（EKF 0.22–0.90%、庫倫 1.72–1.98%、阻抗 23–31%）＝管線交叉驗證
- **內容三軸（精度／強健性／footprint）＋核心賣點「量測域一致性凌駕演算法選擇」全數濃縮成 6 頁**；11 篇參考文獻皆實際引用（無孤兒），全取自論文既有 IEEE 清單
- 依使用者要求把輸出檔名改為論文英文題目（原 `TANET_SOC_estimation_embedded` → `A_Comparative_Study_and_Embedded_Implementation_of_SOC_Estimation_Methods_for_Lithium-ion_Batteries`，底線串接比照參考檔風格），build/to_pdf 腳本輸出名同步

#### 🐛 問題與踩坑
- **Git Bash 的 `python3` 打到 Windows Store alias 直接失敗**（Python was not found）；一律用 `python`，中文輸出加 `PYTHONUTF8=1` 並寫檔避開 cp950 console 亂碼
- **docx 表格跨欄斷裂**：Table 2 的 header 被孤立在左欄底、body 落到右欄頂 → 對每列加 `w:cantSplit`＋非末列 `keep_with_next`，且把 caption 改置於表上並 keep_with_next，整塊才不被欄界切開（表題置上也才符合慣例／參考檔）
- **參考檔一開始找不到**：使用者用 AskUserQuestion 的 Other 填了英文檔名，實際在 `DOC/研討會報告/refer/`（當天新建）；靠 `AppData/Roaming/.../Recent/*.lnk` 與全碟 find 才定位
- **簡體字誤植**：Chinese 摘要一度打成「鲜少」「锂離子」，建置前用繁體修正（鮮／鋰）

#### 📋 待辦
- 學生 email 已填真實學號信箱 `g11277602@cycu.edu.tw`（指導教授 wkcheng@cycu.edu.tw）；送印前僅剩確認**作者英文拼音**（暫用威妥瑪 Ta-Chia Hung；參考檔用漢語拼音風格，可改 Da-Jia Hong）
- 使用者在 Word 目視投稿論文 docx 最終排版；若要改中文正文版可切換
- 論文其餘既有待辦（封面三項、方程式編輯器重排等）延續

### 2026/07/21（論文六章全面潤飾去艱澀＋產出新版 `_20260721.docx`＋合併遠端 13 篇可下載文獻）

#### ✅ 完成項目
- **六章 md 全面潤飾**（正式學術文風、去艱澀、清撰稿殘留）：反問題病態→「亦即由動態阻抗反推 SOC 對量測誤差過度敏感」、條件數→「反解問題的本質敏感度」、oracle 上界→「假設每次都選對分枝的理想上界，線上並無此種事後保證」；**刪 4.2/4.3 兩段「已完成」進度備註**、清掉各章「章節草稿」註記/`[待補引用]`/內部程式名（perf_cyc/round_runner/BenchInterlock/cycle_log→正式敘述）/`[論文大綱.md]` 連結；**補回缺漏的 4.3.3「演算法與估測流程」**使 4.3 節次連續、內文引用同步正確
- **產出全新 `_20260721.docx`**（54 頁）：保留 `_20260720` 的封面/目錄/圖檔/方程式格式，用 **Needleman-Wunsch 全域對齊**把潤飾後 196 段正文替換進去（刪 3、插 1）、重建粗體與行內數學式；Word COM 全自動更新三份目錄頁碼、逐頁 PDF 目視驗證
- **dwell→停留**全篇統一（md+docx，13 處＋清中文間誤插空格 25 處，保留「停留 1 秒」「原為 1 s」）
- **LaTeX 行內漏出全修**（使用者發現「mathbf 像程式變數」）：改良轉換器處理 `\mathbf`/`\partial`/`\cos`/`\tan`/`\max`/`\text{}`＋單數字下標（R_0→R₀、V_1→V₁），重建 6 段；`R_shunt` 轉真下標 run；表 2-1 ECM 全乾淨。（比較指標公式表與方塊方程式仍為線性近似，屬 Word 方程式編輯器範疇）
- **合併遠端 13 篇可下載 arXiv 文獻**（origin/main 領先的兩筆改版）：參考清單 5→13（[3][4][5] 由 Plett/He/Weppner 換成 Hasan/Song/Qin，[6]–[13] 新增），**內文引用 15 處逐句重新對應**（ECM [4]→[9]、UKF [3]→[7],[10]、商用IC [3]→[12]、GITT 去[5]、pseudo-OCV +[12]、遲滯 +[13] 等）；md 與 docx 皆更新並逐條核對、參考頁渲染確認 13 條齊全

#### 🐛 問題與踩坑
- **docx 的「[n]」引用與英文詞（dwell/mathbf）是獨立 run**，逐 run replace 對不到跨 run 字串；需「跨 run span 取代」（把命中的 span 收攏到首個重疊 run、保留 span 外的粗體）才成功
- **圖 4-6 後「三個層次」段被誤設置中**（style=Normal 卻 align=CENTER，插圖時繼承圖說置中）→ 導致 `collect()` 略過該段、潤飾對齊時重複（舊「條件數」殘留＋新「本質敏感度」並存）；修法：套用前先把「誤置中的正文段」改回兩端對齊
- **貪婪對齊在大幅改寫段會級聯錯位**→改用 Needleman-Wunsch 全域最佳對齊才穩
- **行內巢狀數學式**（`e^{-\Delta t/\tau_1}` 的 τ_1 在指數內）單層轉換器處理不了 → 在 conv_sym 先把 `_數字`→Unicode 下標，巢狀也一起轉
- **檔案被鎖無法存**（OneDrive 同步或 Word 開著）→ python-docx save PermissionError；需先關 Word/等同步，暫存檔取代亦會被鎖
- **git 分岔**：遠端把文獻整套改版（連 [3][4][5] 都換論文、內文引用逐句重對應）與本機潤飾改到同一批 md → 只能手動合併（以本機潤飾＋套遠端文獻對應），非機械換號

#### 📋 待辦
- **git 收尾未完**：本機潤飾＋文獻合併大量變更待 commit；遠端領先 2 筆（含 11 個參考 PDF、`_20260715.docx`）；md 兩邊都改過，commit 後需 rebase/merge、以本機為準解衝突、PDF 從遠端帶入、再 push
- 比較指標公式表與方塊方程式定稿時用 Word 方程式編輯器重排
- 封面三項（姓名/指導教授佔位）、使用者在 Word 目視 `_20260721.docx`



#### ✅ 完成項目
- **產出論文新版 `_20260720.docx`**（54→55 頁，原 `_20260713` 未動）：新增圖 4-6、補圖目錄/表目錄、補動態阻抗三種失效型態段落，所有欄位以 Word COM 全自動更新並逐頁 PDF 目視驗證
- **圖 4-6 四法 SOC 軌跡比較圖**（`figures/_gen_ch4_soc_compare.py`）：2×2 面板（0.5/1.0/1.5/2.0C），疊繪儀器庫倫真值＋板端庫倫/EKF/動態阻抗，各面板標 RMSE。刻意選 **Round 41**（`mcu_soc_log_20260707_210836.log` 對齊 `round041_cyc189–192` CSV）與論文表 4-2/4-4 同輪，算出 RMSE（EKF 0.22–0.90%、庫倫 1.7–2.0%、阻抗 23–31%）與分析紀錄完全一致＝管線交叉驗證。插入 4.4.1 表 4-4 之後
- **List of Figure／List of Table 改真 Word 欄位**：19 段圖表標題掛新建 FigCaption/TblCaption 樣式（`TOC \t "圖標題,2"`／`"表標題,2"`），Word COM 更新出真實頁碼（圖 9 條、表 11 條、主目錄同步）
- **4.3.4 新增「線上軌跡之三種失效型態」段**（md＋docx 同步）：鏡像跳變（選錯根→跳頂點鏡像側，真值90%→另一根27%）、頂點夾限平台（Z<曲線最低33.4mΩ→判別式無實根→夾限58.6%；Round 41 中 111/425 事件=26% 落此，已用韌體 `soc_zdyn.c:73-77` 與 log 統計實證）、無不確定度加權（每事件獨立重錨、無共變異數降權）；4.4.1 圖說與結論段亦補 Round 42 分枝修正防禦句
- **口試簡報補第 17 頁「三法 SOC 軌跡實測對照」**（圖 4-6＋三失效卡片＋噪聲交叉印證），20→21 頁，footer 全改 /21，講稿同步插入第 17 頁敘述稿並重編號後續四頁
- **口試簡報第六章兩頁全面白話化**（結論決策表＋研究限制/未來工作）：術語換日常講法（SOH→健康度、in-sample→自己驗自己、fleet learning→多顆電池上雲端一起學、rate capability 平坦→大電流也幾乎不掉電量），表格欄名改「產品是什麼情況/建議用哪個/為什麼/要付出的代價」
- 講稿「動態阻抗文獻主推」→「本研究主要研究方法」，簡報第 7 頁表格同步（`build_defense_ppt.py`）

#### 🐛 問題與踩坑
- **docx pack.py 在 cp950 環境誤判 UTF-8 為非法多位元組**：改設 `PYTHONUTF8=1`（比 PYTHONIOENCODING 徹底）即全驗證通過，不必 --validate false
- **範本 toc 1 樣式被 autoRedefine 污染成 48 半點置中**→目錄條目全爆大；移除 autoRedefine 並改 sz 24＋標楷體才修好
- **圖表目錄長標題換行後出現整行純點點再接頁碼**：根因是點狀引線定位點（8296）在文字右界（9071）左側→文字排過定位點→tab 整組被擠到下一行。修法：加右縮排 480（文字提早換行）＋把右對齊定位點移到縮排區內 8900（永遠在文字結束點右側），保證「文字＋引線＋頁碼」同一行
- **前置頁靠大量空白段落填頁**導致近空白頁；改各節標題 `pageBreakBefore` 分頁並刪除約 100 個填充空段落
- **圖 3-2／圖 4-5／表 5-2 圖說整段粗體**（與其他「僅標號粗體」不一致）已拆 run 修正；第二章正文兩處 markdown 殘留連結 `[論文大綱.md]` 已清（docx＋md）
- **pptx sidebar_note 卡片文字溢出色塊**：底部卡片文字過長掉出色塊下緣→縮短文字＋右欄整體上移即修正；表格 cell 避免用 `\n`（單 run 不穩），靠 word_wrap 換行

#### 📋 待辦
- 使用者確認：論文正文（第二章 docx＋論文大綱）的「文獻主推」是否也統一改「本研究主要方法」（語意不同，暫未動）
- 口試簡報是否要把第六章以外頁面（校正、動態阻抗、比較）也白話化一遍；講稿是否跟兩頁新用字同步
- 封面三項（研究生姓名／指導教授為佔位）、第五六章正文既有待辦延續
- 使用者在 Word（標楷體環境）目視確認 `_20260720.docx` 最終排版

### 2026/07/15（論文參考文獻擴充：5 篇 → 14 篇）

#### ✅ 完成項目
- **參考文獻由 5 篇擴充至 14 篇**，產出新版論文 `_20260715.docx`（原 `_20260713` 未動、36 個 zip 條目完整、XML 合法驗證通過）
- **新增 9 篇皆為該領域公認真實文獻**，且每篇都在正文實際引用（無孤兒文獻，避免口試最常見挑剔）：
  - [6] Kalman (1960) 卡爾曼濾波原始論文 → 2.3 KF 原理段
  - [7] Plett (2006) Sigma-Point KF、[8] Sun et al. (2011) Adaptive UKF → 2.3 UKF 段
  - [9] Ng et al. (2009) Enhanced Coulomb Counting → 2.2 庫倫計數弱點段
  - [10] Xiong et al. (2018)、[11] Hannan et al. (2017) SOC 估測綜述 → 1.2 方法分類
  - [12] Hu et al. (2012) 等效電路模型比較 → 2.1 二階 RC 段
  - [13] Waag et al. (2013) 電池阻抗特性 → 4.3 動態阻抗老化指標
  - [14] Roscher & Sauer (2011) LFP OCV／遲滯建模 → 2.1 遲滯段
- **docx 與 markdown 雙邊同步**：第一、二、四章 markdown（source of truth）同步補上引用標註與各章文獻清單；docx 驗證 [6]–[14] 各出現 2 次（1 正文＋1 清單）

#### 🐛 問題與踩坑
- **docx 改動延用既有紀律**：`zipfile` 讀原始 `word/document.xml` 做 `str.replace` 再原樣重打包，不用 python-docx 整檔重存（保護 VML／namespace）；新文獻段落直接 clone 既有 [5] 的 `<w:p>` 區塊（含 pPr 懸掛縮排、Times New Roman rPr）換文字，確保排版一致
- **每個 str.replace 都先斷言恰好命中一次**（count==1 才執行），避免跨章誤植；插入引用前用 Windows cp950 踩坑教訓一律 `PYTHONUTF8=1` 跑 python
- 錨點字串一度把「審慎」誤打成「審慕」，靠 count 驗證擋下、修正後才過

#### 📋 待辦
- 文獻 [6]–[14] 卷期／頁碼按公開書目填入，正式送印前建議照學校格式再核對 DOI
- 口試簡報參考文獻頁可視需要補上這 9 篇（本次未動；使用者指示講稿不需更新）
- 論文其餘既有待辦（封面三項、第五六章、方程式編輯器重排、docx 目視確認）延續

### 2026/07/10（動態阻抗精度改善：融合/分箱平均/分枝修正＋Round 42 板端實測驗證）

#### ✅ 完成項目
- **針對「動態阻抗線上精度太差」提出四層解法並落地程式**：量測層（加大 ΔI／平均／溫補）、模型層（拆 R0/R1、多時間尺度）、演算法層（靈敏度閘控＋EKF 融合）、定位層（重新框定為 SOH／端點用途）
- **§3 靈敏度加權融合**（`soc_ekf`＋`soc_zdyn`＋`userCode`）：新增 `soc_ekf_correct_soc()` 直接 SOC 觀測路徑（C=[1,0] 純量更新、Joseph form）；zdyn 事件解出 SOC 後算局部靈敏度 g=|2a·SOC+b|、導出量測變異數 R=(σ_Z/g)²，過門檻才登錄；`soc_zdyn_take_gated_event()` consume-once 餵 EKF。閘控區間實測 SOC≤36%／≥81%（中段 37–80% 病態區閘掉）
- **§A 分箱平均降噪＋庫倫錨定分枝**（`soc_zdyn` 重構）：加內建庫倫參考（協定自滿電起放）為 SOC 索引，同箱 Z 累積平均後才反解（√N 降噪，複刻論文離線平均管線）；分枝改取距庫倫參考最近之根，取代脆弱的趨勢判斷
- **host 模擬 harness**（編譯實際韌體 C 模組 soc_ekf.c/soc_zdyn.c）：用真實放電 trace＋真 GITT OCV 表驗證，1s ZOH 重取樣保留擾動階躍；含 oracle-branch 評估法隔離 Z 雜訊
- **燒錄 Round 42 完整一輪四倍率板端實測**（~16h）：新韌體 + UART logger 並行記錄，epoch 對齊 bench 庫倫真值
- **板端實測結果**：EKF **0.45–1.44%**（1.0C 0.48%，三法最佳）、庫倫 1.8–2.2%、動態阻抗 12–21%（中段 40–60% 仍 19–30%、低段高倍率降至 4.9%）
- **分枝修正把線上動態阻抗從 Round 41 的 23–31% 降到 12–21%**（正好打中論文點名的兩個根因：46% 選錯根、噪聲）；但仍遠輸 EKF、中段病態依舊、且需庫倫輔助分枝 → 結論不變
- **確認論文已完整（六章 0 個 [待測]）**：EKF 精度／footprint／動態阻抗離線-線上誠實區分早由 Round 40/41 補完；Round 42 只是再確認，結論與實測一致

#### 🐛 問題與踩坑
- **量測域不匹配大坑**：台架端 trace（含 ~24mΩ 線材電阻）餵板端係數（c=39.6）→ 二次反解整個平移、判別式恆無實根 → standalone RMSE 爆到 54%。host 驗證台架 trace 必須用台架係數（a=20.2/b=−21.6/c=63.6）
- **融合會傷已 <1% 的 EKF**：σ_Z 假設 2mΩ 但單次事件實際散布達 ±數十 mΩ → EKF 過度信任噪聲觀測，0.70%→3.88%。故 `SOC_ZDYN_EKF_FUSE` **預設關閉**，程式路徑保留給 SOH／初值實驗
- **分箱平均在單次放電內幫助有限**：一次放電僅 ~220 事件／20 箱 ≈ 11/箱，遠不及壓低 ±50mΩ 散布所需的數百/箱；論文 6–10% 是跨輪離線聚合來的。Round 42 因四 cycle 間未 reset，箱跨 cycle 累積（天然的跨循環聚合），但中段病態救不了
- **benchdomain model_set 副本未含新分箱參數 → 編譯失敗卻 silently 跑到舊 binary**，數字全一樣才發現；sed 改 C 係數時 pattern 寫成 63.6→63.6 no-op（源檔實為 39.6）重蹈量測域混淆
- **先前基於過時 CLAUDE.md 誤判論文有 [待測]**：實際第四章早被 Round 40/41 徹底更新、0 待測。動筆前務必讀實際論文而非舊筆記
- **EKF 初值恢復極快**：故意設錯 60%（真值 100%），baseline RMSE 仍 0.70%——電壓觀測在 NMC 斜率 OCV 下幾乎單步拉回，zdyn 初值錨定的邊際價值在此有限

#### 📋 待辦
- 論文可選加分：4.3.4 補一句「後續庫倫參考分枝＋跨cycle分箱把線上 RMSE 由 23–31% 降至 12–21%，惟需庫倫輔助分枝、中段仍病態，結論不變」當口試防禦（堵「有沒有試更好分枝」）
- 板端已燒 Round 42 新韌體（分枝修正＋分箱平均＋融合關閉）
- 論文其餘既有待辦（封面三項、第五六章、方程式編輯器重排、docx 目視確認）延續

### 2026/07/09（論文 20260707 排版修正：字距撐開與紅字）

#### ✅ 完成項目
- 診斷 `_20260707.docx` 內文「有些字那麼開」成因：內文段落為兩端對齊（both），遇不能斷行的英文縮寫（MATLAB／SOC／MCU／OCV／RMSE）時整串英文被推到下一行，剩下的中文行被強制撐滿整寬 → 字距拉開；確認非資料損毀（run 僅有正常 `w:kern`，無 run 層字距膨脹）
- 依使用者選擇試把內文 197 段（192 內文＋3 條列＋2 其他）由 both 改 left 靠左對齊；使用者反映靠左後右邊界參差、英文縮寫卡行尾的斷行更奇怪，最終決定改回兩端對齊
- 表格內 44 處實測數據深紅字（`w:color C00000`）全部改黑字（000000）
- 最終定案檔：兩端對齊 197 段回復、原靠左標題／圖說 308 段不動、紅字歸零、8 張圖完整、XML 合法；就地存回同一版（未進版）

#### 🐛 問題與踩坑
- docx 改動一律用 zipfile 讀 `word/document.xml` 原始字串做 `str.replace` 再逐 entry 原樣重打包，不用 python-docx 整檔重存（避免破壞 VML／namespace）
- **git checkout HEAD 還原陷阱**：為精準還原靠左實驗（不能無腦把 505 個 left 全改回 both，會誤傷原本就該靠左的 308 段標題），改從 git 拉回原檔——卻發現工作區那份被 Word／LibreOffice 重存過而膨脹（1.9MB／52 entries），git HEAD 是精簡 build 版（994KB／36 entries）；session 起始 git status 顯示 clean 是舊快照，實際工作區為 dirty。經逐項比對（摘要 621 字 byte-exact、8 圖全在、各章／參考文獻齊全）確認 document.xml 內容一致、無內容損失，差異僅打包附加物（縮圖／頁首／customXml）
- 中英混排先天取捨：兩端對齊→字被撐開、靠左→右邊參差，無法兩全；正式中文論文以兩端對齊為標準

#### 📋 待辦
- 使用者在 Word（標楷體環境）目視確認最終排版；若某幾行撐開過於誇張可局部微調（關鍵縮寫前後塞不換行空格）
- 論文其餘既有待辦（封面三項、EKF/footprint 實測數字、第五六章、方程式編輯器重排等）延續

### 2026/07/02（三種 SOC 估測法韌體實作＋圖 3-2＋論文進版）

#### ✅ 完成項目
- **三種 SOC 估測法全部落地 STM32G071 韌體**（USER_CODE 新增四模組）：
  - `soc_coulomb`：純整數庫倫計數（int32 µA 輸入、int64 µA·s 累加器、SOC 0.01% 解析度），兼三法比較的 ground truth
  - `soc_ekf`：一階 RC EKF（狀態 [SOC, V1]，ZOH 精確離散化、純量增益免矩陣求逆、Joseph form 共變異數、分段線性 OCV 查表＋段斜率 Jacobian）；OCV 表為佔位（`soc_ekf_ocv_table.h` 標記區，GITT 後由 `gen_ocv_header.py` 重生，佔位表數據不得入論文）
  - `soc_zdyn`：動態阻抗法（1Hz 相鄰樣本抓 ΔV/ΔI 事件、|ΔI| 窗 300–4500 mA、二次式反解＋三層選根：錨點連續性→Z趨勢×電流方向→預設高根；內建 float 庫倫內插自足、可獨立編譯），係數用表 4-3 實測值 a=20.2/b=−21.6/c=63.6 mΩ
  - `perf_cyc`：M0+ 無 DWT CYCCNT，用 SysTick 夾擠讀法（tick-stability do-while 處理 reload race）量每次 update 的 cycle 數
- **Footprint 量測管線**（論文 4.4.3 依據）：enable 旗標全部 `#ifndef` 包裝、Makefile 加 `EXTRA_CFLAGS` hook，`SCRIPTS/footprint_report.py` 自動編 5 個變體做差分。首批數據（-Og）：base flash 60940/ram 4840；庫倫 +1124/+20、EKF +1868/+40、動態阻抗 +1456/+48、全開 +3904/+104
- `userCode.c` 掛載：`soc_estimators_feed_1s()`（EKF 首筆電壓自 seed、每法 update 各自計 cycle）＋每秒一行 `soc cc=..% ekf=..% z=..%` UART 回報
- **圖 3-2 韌體方塊圖**（`figures/_gen_ch3_fw.py`）：正式 matplotlib 圖檔，風格比照圖 3-1；第三章 markdown 3.2 補掛載關係段落＋插圖
- **論文進版 `_20260702.docx`**：從 _20260625 複製後後製——3.2 收尾段補句、fig3-2 以模板複製法插入（deepcopy fig3-1 圖段/圖說段、改 rId/extent/docPr），md 與 docx 同步
- 更新 `MCU/README.md`（§5 估測模組表＋UART 格式＋footprint 數據）、`project.yaml`（四模組入 scaffolded、soc_soh_calc 標 SUPERSEDED）

#### 🐛 問題與踩坑
- **產圖標籤重疊三連坑**（使用者退件「字跟圖不要重疊」）：箭頭標籤「中點＋偏移」放法會壓斜線／方塊角。修法：`arrow()` 改絕對座標 `lpos`＋幾何檢核（標籤全寬對箭頭線算 y、離線離框 ≥0.3 單位）；窄縫塞不下五字標籤時**改版面**（上下對調方塊讓四字標籤進窄縫）而非硬塞；產完必 Read PNG 目視。已寫入記憶 `figure-label-no-overlap.md`
- python-docx `doc.part.get_or_add_image()` 回傳順序是 **(rId, image)** 不是 (image, rId)；rels 路徑是 `word/_rels/document.xml.rels`
- docx 換圖 bytes 用 zipfile 重打包即可；長寬比沒變就不用動 extent
- 樹莓派 venv 缺 matplotlib（pip 裝 3.11.0 via piwheels）；中文字型用 Noto Sans CJK TC 替代微軟正黑

#### 📋 待辦
- 板子接回後燒錄實測（`flash_and_verify.py`），取得三法每次 update 的實測 cycle 數填表 4-6
- GITT 跑完 → `gen_ocv_header.py` 重生 OCV 表；脈衝最小平方辨識 R0/R1/τ1 填 MODEL_SET_SOC_EKF（現值全為 [待測] 佔位）
- EKF PC 原型調 Q/R；4.4.2 強健性測試
- `_20260702.docx` 待 Word 目視確認＋F9 更新圖目錄欄位
- 舊 `soc_soh_calc` stub 移除
- 封面三項、誌謝、第五六章仍未完

### 2026/06/25（口試簡報製作與封面／章節修正）

#### ✅ 完成項目
- 新建 `build_defense_ppt.py`：用 python-pptx 從六章 markdown 萃取重點，產生 **20 頁口試簡報** `口試簡報_鋰電池SOC估測.pptx`（16:9、電資學院銀灰藍配色、嵌入論文 6 張正式圖檔＋實測數據表）。頁序：封面→大綱→背景→動機→目的貢獻→文獻→方法選擇→系統架構→韌體骨架→INA226校正→測試協定→庫倫→rate-capability→EKF→動態阻抗原理→動態阻抗實測→三方法比較→系統整合→結論決策表→限制未來工作
- 撰寫 `口試講稿.md`：逐頁敘述稿（約 12–15 分鐘）＋ 5 題委員口袋題庫（庫倫當真值、EKF 未測完、動態阻抗 RMSE、為何不用 2RC/UKF、能否外推）
- 章節用字修正：「3.2 韌體骨架與系統節拍」→「3.2 韌體骨架」，同步改第三章 markdown、簡報、講稿、兩份 docx
- 第 9 頁韌體骨架改用**原生 PowerPoint 方塊圖**（節拍→once/loop→模組化 pipeline，SOC 估測模組綠色標示為三法掛載點），避免缺字型 tofu
- 依使用者回饋多輪白話化＋強化：研究動機（兩缺口改口語）、三點貢獻（①改「讓公平比較成立的量測方法」、③改「首次同硬體公平基準＋決策表」，破解牽強感）、庫倫計數說明框（去術語）

#### 🐛 問題與踩坑
- **封面標題兩行重疊**：python-pptx 設 `line_spacing` 倍率擋不住——缺 Microsoft JhengHei 時替代字型行高被壓縮。改用**兩行各自獨立文字框、固定 Y 座標**才根治
- **docx 封面書背壓住標題**（VML `<v:shape>` 直書框跑到頁面正中）：補 `mso-position-horizontal:absolute` token 仍無效（多檢視器都不吃）→ 最終**直接移除整個 `<w:pict>` 區塊**。教訓：VML 浮動框定位不可靠，書背交裝訂廠、別疊封面
- **改 docx 別用 python-docx 整檔重存**：lxml 重新序列化會破壞 VML namespace。只改幾個字要用 `zipfile` 對 `word/document.xml` 原始字串 `str.replace()` 再 `writestr` 重打包，其餘 entry 原樣搬移
- 本機 LibreOffice（樹莓派）轉 PDF 極慢／逾時，且對 VML 定位解讀與 Word 不同，預覽不可信

#### 📋 待辦／提醒
- 封面三項佔位待填：研究生姓名、指導教授（`[ ]` 佔位）
- docx 待在 Word（標楷體環境）做最終視覺確認
- 簡報數值與論文同步：EKF 精度、三法 footprint 仍為 [待測]
- 詢問中：是否把第一章 1.3 三點貢獻、其他頁說明框同步白話化／把韌體骨架方塊圖補進論文當圖 3-2

### 2026/06/25（論文排版校正與 SCPI 段落同步）

#### ✅ 完成項目
- 下載中原大學官方論文範本（圖書館 `word_thesis_template.zip`，內含 2025-06-10 更新的 `論文中文範本1.docx`）與最新格式規範（113-2 學期 PDF），逐條核對主檔排版
- 依規範＋範本修正主檔 `_20260625.docx` 四項排版：(1) 版面邊界改為規範值 上2／下2／左3／右2 cm；(2) 章標題 Heading 1 由 Word 預設藍 `2E74B5` 改黑；(3) 封面中文題目 16pt→22pt 並補左側直書書背（VML 浮動文字框，相對頁面絕對定位）；(4) 全文 166 處底線變數 `V_t`／`R_0` 等轉成 Word 真正下標/上標（共 186 run）
- 確認規範符合項：裝訂次序、前置頁羅馬數字+正文阿拉伯數字、摘要中英分頁、A4、內文標楷體非粗體；剩 8 條分數/積分式（`(1)/(R_1 C_1)`、`∫` 上下限）留待 Word 方程式編輯器手排
- 同步「SCPI 陷阱」段落：第三章 markdown 早已刪除 3.4 SCPI 自動化（含陷阱一 APPL／陷阱二 PSU-off 殘留電流）並重構，但 docx 仍為舊版；本次將 docx 對齊 markdown——刪 ch3 SCPI 整段（3.5 跨輪→3.4）、刪 ch5 5.4.1 儀錶段（5.4.2→5.4.1、5.4.3→5.4.2）、修 ch5 5.4 開頭/共通原則/小結與 ch6 結論共 4 處孤兒引用（「不信任指令即生效」原則隨之移除，三條→兩條）
- ch5/ch6 的 markdown 與 docx 兩邊都改；docx 段落重建時以 `**` 解析保留粗體強調

#### 🐛 問題與踩坑
- `build_thesis.py` 不在 repo（在 Windows 那台、未 commit）→ 本機只能直接後製 docx；docx 與 markdown 需手動保持同步，落差目前僅侷限於 SCPI 段
- python 腳本命名 `inspect.py` 會 shadow 標準庫導致 lxml 初始化 circular import；改名即解
- python-docx 無法用 `OxmlElement('v:shape')`（VML `v:` namespace 未註冊）→ 改用 `parse_xml` 帶 nsdecls 手寫 VML
- 書背 VML 定位：Word 對 `mso-position-horizontal:left` 關鍵字解讀與 LibreOffice 不同（LO 靠左、Word 跑到正中壓住標題）→ 改用 `margin-left/top` 絕對值相對 page 定位才穩
- probe 偵測粗體用「`<w:b>` 標籤存在與否」會誤判（內文其實是 `w:val="0"`），須讀 val 才準

#### 📋 明日待辦
- 8 條分數/積分式用 Word 方程式編輯器重排
- 封面三項（研究生姓名／系所全名／指導教授）、誌謝個人內容
- EKF（4.2.5）精度、三方法 footprint（4.4）仍為 [待測]
- docx 待在 Word（有標楷體環境）做最終視覺確認

### 2026/06/11（下午　論文全面修訂）

#### ✅ 完成項目
- 第四章演算法／實作改用正式圖檔（matplotlib 產生，存 `論文撰寫/figures/`）：圖4-1 庫倫流程、圖4-2 EKF 預測-更新遞迴、圖4-3 動態阻抗離線建表+即時估測流程、圖4-4 動態阻抗實測擬合；移除含實作術語（64-bit 累加器等）的資料流圖
- 戴維寧等三種等效電路畫成圖2-1（電路示意圖：內阻／一階RC／二階RC）
- **動態阻抗係數實測算出**（fresh rounds 1–3 擾動段）：合併 a=20.2、b=−21.6、c=63.6 mΩ，最低點 SOC≈53%（符合理論50%），高倍率擬合殘差低至0.5mΩ、低倍率3.5mΩ（印證SNR說法），填入表4-3
- 庫倫積分公式取消庫倫效率 η（Ch2 2.2.1、Ch4 4.1.1／4.2.1）
- 移除資料驅動法／神經網路（Ch2 2.2.5＋分類改兩類＋2.4表；Ch1 分類／未來工作）
- 「Lin」不以人名表示，全部改文獻編號 [n]
- 取消 Ch3 3.5 BenchInterlock、3.7 GITT，章節重新編號（3.6→3.5），表3-4 改成易懂的「一組四步驟、只差放電倍率」排版
- 3.2 韌體骨架、4.1.3／4.2.4／4.3.4 實作節改寫成淺顯白話、不放程式變數名（面向非程式背景讀者）
- 參考文獻：移除 Lee(NN)，重新編號，補入 Plett(EKF)／He(ECM)／Weppner(GITT) 真實出處（卷期頁碼標待核對）
- 建置腳本升級支援圖片嵌入＋docx 參考文獻區塊更新，重建 `_20260611.docx`（5 圖、5 參考文獻、14 表）

#### 🐛 問題與踩坑
- matplotlib 中文用 Microsoft JhengHei；缺字（≈、−、ᵀ）需改寫或以線段繪製；數學式用 mathtext(stix) 排版乾淨
- 本機 `python`(Desktop/.venv) 無 python-docx，需用 `C:\...\Python312\python.exe` 跑

#### ✅ 補完成（傍晚續工）
- **docx 第一章已同步**：`build_thesis.py` 升級為「Ch1 也從 `第一章_緒論.md` 重建」（移除 pristine 舊正文、保留其後參考文獻區塊再更新）；驗證 Ch1–4 已無 NN／資料驅動／Lin 等人／庫倫效率／round_runner／heartbeat／soc_soh_calc，內文引用編號 [1]–[5] 一致
- 圖3-1 系統架構改成正式圖檔（`figures/fig3-1.png`），docx 共 6 張圖（圖2-1、3-1、4-1～4-4）
- Ch4 4.0、4.1.4、Ch3 3.1 殘留術語淺顯化（去 soc_soh_calc／100µs／heartbeat／round_runner／cycle_log 等）
- 踩坑：python-docx `doc.paragraphs` 每次回傳新 wrapper，段落比對要用 `p._p is x._p`（XML 元素身分），不能用 `p is x`
- **動態阻抗「反推 SOC」逐點精度實測算出**：用表4-3 係數把阻抗反解成 SOC、與庫倫真值比（oracle 分枝），各倍率 RMSE 約 6～10%（0.5C 9.7%、2.0C 6.3%）；SOC 中段40-60% 較差（9-13%）、兩端較小（5-9%），印證拋物線中段平緩→反推病態；rounds1-2擬合/round3留出驗證 RMSE 7-10% 相當（非過擬合）。填入表4-3 末欄、表4-4 動態阻抗列，並補進 4.3.4／4.5 內文

- 中文摘要＋英文 Abstract＋雙語關鍵詞已撰寫並填入 docx 前置頁（誠實版：只陳述已完成實測，EKF/footprint 不報數字）；建置腳本加 `fill_placeholder()` 取代佔位

#### 📋 還沒做完（明日待辦）
- EKF（4.2.5）精度、三方法 footprint（4.4）仍為 [待測]（需先建 GITT OCV 表、做 EKF 原型與移植）
- 誌謝（個人內容）、封面三項（研究生姓名／系所全名／指導教授，需使用者提供）、第五六章內文
- docx 待 Word 視覺確認；數學式仍線性近似，待方程式編輯器重排
- 動態阻抗「以擬合反推 SOC」的逐點精度尚未計算（目前只算了擬合係數本身）
- docx 尚未經 Word 視覺確認（本機無 PDF 轉檔工具）；數學式仍為線性近似，待 Word 方程式編輯器重排
- 摘要／Abstract／誌謝／封面三項、第五六章內容仍待寫

### 2026/06/11（上午　第四章初稿）

#### ✅ 完成項目
- 撰寫第四章完整草稿 `第四章_SOC估測方法之實作與比較.md`：4.0 共同前提（SOC 真值界定、比較指標符號）、4.1 庫倫計數（兼 ground truth）、4.2 EKF（一階 RC、狀態 2 維、增益免矩陣求逆、GITT OCV 表觀測方程）、4.3 動態阻抗（複用 dV/dI 擾動、二次擬合＋分枝選根）、4.4 三軸比較框架、4.5 小結
- 嚴格區分實測與待測：rate-capability 真實數據入文（rounds 1–23，0.5C→2.0C 容量僅降約 1%、跨輪再現性佳）；EKF／動態阻抗／footprint 數值一律標 `[待測]` 紅字佔位，不虛構任何 RMSE
- 第二、三、四章全部併入論文主檔，產出 `鋰電池SOC估測方法之比較與嵌入式實作_20260611.docx`（549 段、15 表），格式逐項比照第一章（節標題粗體 14pt 靠左、內文標楷體 12pt 首行縮排兩端對齊、表頭淺藍底）；原主檔未動
- 建立 md→docx 轉換管線（python-docx）：markdown 解析（標題／內文／表格／公式／程式碼／註記／表標題）＋ LaTeX→unicode 線性近似 ＋ 表格自動配寬與框線
- 依使用者要求把內文行距 18pt → 24pt（181 段），標題／表格／註記／程式碼維持原樣

#### 🐛 問題與踩坑
- LaTeX 轉換器 `\in` 規則先吃掉 `\int` 產生「∈t」亂碼；`\dfrac` 未涵蓋——改用整字 regex（`\\([a-zA-Z]+)` 查表）＋ dfrac 正規化 ＋ 殘留花括號清除解決
- docx skill 的 `soffice.py` 在 Windows 用 `socket.AF_UNIX` 直接 AttributeError，PDF 視覺驗證不可行；`validate.py` 缺 `defusedxml`——改用 python-docx 做結構驗證（章界、樣式、表格 shape 抽查）
- python-docx 對混排插入要用 `cursor.addnext(element)` 逐塊推進，表格（`w:tbl`）與段落（`w:p`）才能保持原文順序

#### 📋 明日待辦
- 撰寫摘要／Abstract／誌謝內容、補封面三項（研究生姓名、系所全名、指導教授）
- 第五、六章內容撰寫（主檔仍為佔位）
- 第四章 `[待測]` 實驗排程：GITT OCV 表建立、EKF PC 原型、動態阻抗離線擬合
- Word 內數學式改方程式編輯器重排；圖 3-1／3-2 ASCII 圖改繪正式向量圖

### 2026/06/03

#### ✅ 完成項目
- 確立碩論主題銳化方向：以「嵌入式資源約束下的 SOC 演算法精度-成本權衡」為論文記憶點，三方法（庫倫計數／EKF／動態阻抗）退為實驗載體，避開「純比較缺乏新穎性」的口試攻擊
- 撰寫第一章緒論完整內文：1.1 研究背景、1.2 研究動機（兩個 research gap：評估環境失真、benchmark 不公平）、1.3 研究目的與貢獻（三點）、1.4 論文架構，含三篇參考文獻（Lin 2016／Bressanini 2017／Lee et al.）
- 基於中原官方 Word 範本產出論文主檔：封面（中英題目、碩士學位論文、民國 115 年）＋ 摘要／Abstract／誌謝佔位框架 ＋ 第一～六章框架
- 緒論內文併入主檔第一章，套正式論文格式（節標題粗體靠左、內文標楷體 12pt 首行縮排兩端對齊、貢獻編號、參考文獻懸掛縮排）
- 改為單一 Word 檔持續更新模式（`鋰電池SOC估測方法之比較與嵌入式實作.docx`），刪除日期版本快照（原 `_YYMMDDnn` 命名）
- 清除範本殘留：TOC／TOF 教學快取、9 張孤兒教學截圖（742 KB → 31 KB）、格式說明表

#### 🐛 問題與踩坑
- Windows cp950 codec 在 docx `validate.py` 誤判合法 UTF-8 XML 為非法多位元組，用 `PYTHONUTF8=1` 解決
- python-docx 刪段落（`w:p`）不會刪表格（`w:tbl`），範本「格式說明表」漏刪，改用 `d.tables` 定位刪除
- 範本章標題實際是 Normal＋手動格式（非 Heading 1 樣式），定位正文教學區要用文字比對而非樣式名
- 開檔跳「功能變數可能參考其他檔案」警語，根因是 TOC field 被標記 `dirty="true"`，移除 dirty 即不再跳（並把目錄快取填回六章避免空白）
- pandoc／pdftoppm 未安裝，改用 python-docx ＋ pypdf 處理 docx／pdf

#### 📋 明日待辦
- 將第二章、第三章草稿併入主檔
- 補封面三項（研究生姓名、系所全名、指導教授）
- 撰寫摘要／Abstract／誌謝內容

### 2026/05/12

#### ✅ 完成項目
- 重寫 `round_runner.py` charge step 充飽判斷：條件 `V≥V_cv−100mV` 且 `I≤0.1C` 須**連續滿足 3 秒** + 總 elapsed ≥ 30s，避免 t=0 單點誤觸發
- 新增 already-full bypass：cell 起步 5 秒視窗內若 `V≥V_cv−30mV` 且 `I<50mA` 且未進過 CC，整個 charge step 跳過（log `note=already_full`），免去隔夜飽電 cell 又跑無意義 CV taper
- 把所有充飽 knob 集中到 `run_charge_step` 開頭（`v_term_margin` / `i_term` / `t_term_min` / `term_hold_s` / `full_v_margin` / `full_i_max` / `full_window_s`），附 comment block 解釋兩條路徑
- bypass 視窗期間每秒印一行狀態，避免 30s `_live_print` 間距讓操作者誤判程式卡住
- 修 BenchInterlock 的 `_psu_off_verified`：從「sleep 100ms 後 hard check」改為「**polling 最多 2 秒、提早通過就走**」，每 150ms 量一次 `MEAS:CURR?`

#### 🐛 問題與踩坑
- 第一次 round_runner 跑 step 1 (charge 0.5C) 在 t=0 就 `term` 結束：cell 隔夜 OCV≈4.19V，距 V_cv 只剩 10 mV，I=0（PSU 還沒 ramp）→ 條件瞬間成立，整個 charge step 跳過、ah_in=0
- bypass 第一版 window=3s 在 1 Hz sampling 下只看 3 筆 sample，PSU output 短暫尖峰會打成 `full_seen_break=True`，bypass 被否決且 `cc_entered` 又永遠到不了 → loop 卡死。修法：延 window 到 5s + normal term 解除 `cc_entered` 依賴，改用 30s settle time
- term 觸發後立刻下 `CHAN:OUTP OFF`，100ms 後 `MEAS:CURR?` 仍回 0.1021A（term 時是 0.1041A，僅掉 2 mA），BenchInterlock 50 mA 門檻誤判 PSU 沒關 → emergency stop。根因：IT6302 內部 A/D 約 1-2 Hz，頭幾筆 MEAS 還在回 OFF 前的 cache

#### 📋 明日待辦
- 重跑 round 1 確認 charge step 能正常 term + interlock 通過
- 觀察 cycle_log.csv 的 0.5C cycle `q_retention_pct`（cell baseline 是否 95-100%）
- 若 polling 2s 仍過不了，補上 `VOLT 0` + `CURR 0` 再 OFF 的激進手段，並考慮把 OFF 後第一次 MEAS 結果直接丟掉（強制 flush stale cache）

---

### 2026/05/11

#### ✅ 完成項目
- 完成 INA226 多點線性內插校正：充放電各 7 點（0/0.05/0.1/0.5/1.0/1.5/2.0 A），全範圍誤差 < 0.21 mA（< 1‰）
- 把 14 點 LUT 經 UART CLI 燒進 STM32 flash page 63（0x0801_F800），開機自動載入，heartbeat 多吐 `cal=on` 與 `Ical=`
- 撰寫校正紀錄文件：`DOC/校正紀錄/2026-05-07_ina226_calibration.md` + `2026-05-07_ina226_validation.json`（4 點內插驗證資料）
- 設計並實作跨輪測試協定 `TEST/round_runner.py`：一輪 = 充 0.5C →休30m →放 {0.5/1.0/1.5/2.0}C →休30m，共 4 個放電 cycle
- 加入持久化 `cycle_log.csv`：記錄 cycle_id、round_id、q_retention_pct、cumulative_ah；跨次執行自動續接 round_id
- 為所有 4 個放電 rate 加入 dV/dI 擾動（每 60s 步進到 0.2C dwell 1s），庫倫計數涵蓋擾動秒數避免 ~3% undercount
- 設定當前電池 profile：custom NMC 2000 mAh，V_cv=4.2V，V_cutoff=2.5V，max discharge 4A

#### 🐛 問題與踩坑
- IT6302 `APPL V,I` 對連續寫入不可靠更新 CURR，round_runner 首次充電灌出 2A 而非 1A（校正腳本曾踩過同坑卻沒套用紀律），修法：分開 `set_voltage`+`set_current` + `CURR?` readback 驗證
- 第一版 round_runner 為求 V(SoC) 純淨度移除擾動，使用者反映「動態內阻沒被記錄」後補上；對所有 4 rate 採是因為高 C 的 ΔI 反而給更好 dV/dI SNR

#### 📋 明日待辦
- 今晚 22:00 啟動第一輪 rate-capability round（預估 ~18h），明日下午結束
- 觀察 cycle_log.csv 中 0.5C cycle 的 q_retention 是否落在 95-100%（驗證電池實際容量 vs 標稱）
- 累積 3 輪 fresh-cell baseline 後計算輪間 a_origin 變異性，數據過了才進 Phase 4 老化測試

---

### 2026/04/14 (updated)

#### ✅ 完成項目
- 初始化 git repository 並推送至 GitHub (JackHung9527/SOC_RESEARCH)
- 安裝 PPTX Skill（從 anthropics/skills 下載完整 scripts、schemas、validators）
- 安裝相依套件：markitdown[pptx]、Pillow、defusedxml、pptxgenjs、react-icons、sharp
- 研讀論文「Implementation of SOC and SOH Estimation for Li-ion Batteries」(Lin et al., 2016)
- 規劃 MCU 驗證方案：動態阻抗法 SOC + 投影法 SOH，搭配 IT6302 / IT8512A+ / STM32 / INA226
- 產生 10 頁驗證計畫簡報 meeting_0416_洪大甲.pptx（PptxGenJS）並推送至 GitHub

#### 🐛 問題與踩坑
- markitdown 預設不含 PDF 支援，需額外安裝 markitdown[pdf]
- npm 全域安裝的 pptxgenjs 需設定 NODE_PATH 才能在 node 中 require
- bash heredoc 含中文單引號時產生 EOF 錯誤，改用 Write 工具寫入 .js 檔再執行

#### 📋 明日待辦
- 開始 MCU 韌體架構設計（STM32 + INA226 I2C 驅動）
- 準備硬體接線與 INA226 校準實驗

---

### 2026/04/14 (initial)

#### ✅ 完成項目
- 盤點 SOC_RESEARCH 資料夾內所有檔案，整理檔案清單與分類
- 刪除重複的 3 篇參考論文 PDF（根目錄與 meeting_0326 參考資料夾各一份）
- 建立 DOC / MCU 兩個主要資料夾
- 將所有文件依性質分類搬入 DOC 子資料夾（參考論文、論文簡報、會議紀錄、主題簡報）
- 建立專案 CLAUDE.md，記錄專案概述、資料夾結構、研究主題與慣例

#### 📋 明日待辦
- 開始規劃 MCU 資料夾內的韌體架構與程式碼開發
