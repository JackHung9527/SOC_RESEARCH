// Generates DOC/會議紀錄/meeting_0506_洪大甲.pptx — STM32G071 + INA226 韌體測試流程
// Run: NODE_PATH="$(npm root -g)" node tools/build_test_plan_deck.js

const PptxGenJS = require('pptxgenjs');
const path = require('path');

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5 inches
pptx.author = '洪大甲';
pptx.company = 'SOC_RESEARCH';
pptx.title = 'STM32G071 + INA226 韌體測試流程計畫';

// ───────────── Palette (Ocean Gradient + neutrals) ─────────────
const C = {
    navy:   '21295C',
    deep:   '065A82',
    teal:   '1C7293',
    sky:    'B8D8E3',
    bg:     'F5F7FA',
    line:   'D9DEE6',
    dark:   '1A202C',
    gray:   '4A5568',
    muted:  '8A95A5',
    white:  'FFFFFF',
    warn:   'D69E2E',
    ok:     '2F855A',
    danger: 'C53030'
};

const FONT_HEAD = 'Microsoft JhengHei';
const FONT_BODY = 'Microsoft JhengHei';
const FONT_MONO = 'Consolas';

const W = 13.333;
const H = 7.5;

// ───────────── Helpers ─────────────
function addPageDecor(slide, pageNum, totalPages, title)
{
    // top accent bar
    slide.addShape('rect', {
        x: 0, y: 0, w: W, h: 0.45,
        fill: { color: C.navy }, line: { color: C.navy }
    });
    slide.addShape('rect', {
        x: 0, y: 0.45, w: W, h: 0.05,
        fill: { color: C.deep }, line: { color: C.deep }
    });
    // background
    slide.background = { color: C.bg };
    // title
    slide.addText(title, {
        x: 0.55, y: 0.75, w: W - 1.1, h: 0.7,
        fontFace: FONT_HEAD, fontSize: 28, bold: true, color: C.dark
    });
    // bottom footer
    slide.addText('SOC_RESEARCH  |  meeting_0506_洪大甲', {
        x: 0.55, y: H - 0.42, w: 8, h: 0.3,
        fontFace: FONT_BODY, fontSize: 10, color: C.muted
    });
    slide.addText(`${pageNum} / ${totalPages}`, {
        x: W - 1.5, y: H - 0.42, w: 0.95, h: 0.3,
        fontFace: FONT_BODY, fontSize: 10, color: C.muted, align: 'right'
    });
}

function addBlock(slide, x, y, w, h, headerText, bodyLines, accentColor)
{
    accentColor = accentColor || C.deep;
    // outer card
    slide.addShape('rect', {
        x, y, w, h,
        fill: { color: C.white },
        line: { color: C.line, width: 1 }
    });
    // left stripe
    slide.addShape('rect', {
        x, y, w: 0.12, h,
        fill: { color: accentColor }, line: { color: accentColor }
    });
    // header
    slide.addText(headerText, {
        x: x + 0.28, y: y + 0.12, w: w - 0.4, h: 0.45,
        fontFace: FONT_HEAD, fontSize: 15, bold: true, color: accentColor
    });
    // body
    if (Array.isArray(bodyLines))
    {
        const items = bodyLines.map(t => ({
            text: t,
            options: { bullet: { code: '25AA' }, fontSize: 12, color: C.dark, paraSpaceAfter: 4 }
        }));
        slide.addText(items, {
            x: x + 0.28, y: y + 0.6, w: w - 0.4, h: h - 0.7,
            fontFace: FONT_BODY, color: C.dark, valign: 'top'
        });
    }
    else if (typeof bodyLines === 'string')
    {
        slide.addText(bodyLines, {
            x: x + 0.28, y: y + 0.6, w: w - 0.4, h: h - 0.7,
            fontFace: FONT_BODY, fontSize: 12, color: C.dark, valign: 'top'
        });
    }
}

const TOTAL_PAGES = 11;

// ──────────────────────────────────────────────────────────────
// Slide 1 — Cover
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    s.background = { color: C.navy };

    // Diagonal accent bar
    s.addShape('rect', {
        x: 0, y: 0, w: 0.35, h: H,
        fill: { color: C.deep }, line: { color: C.deep }
    });
    s.addShape('rect', {
        x: W - 4.5, y: 0, w: 4.5, h: 0.45,
        fill: { color: C.teal }, line: { color: C.teal }
    });

    s.addText('TEST PLAN', {
        x: 1.0, y: 1.4, w: 11, h: 0.5,
        fontFace: FONT_HEAD, fontSize: 18, bold: true, color: C.sky, charSpacing: 8
    });
    s.addText('韌體測試流程計畫', {
        x: 1.0, y: 1.9, w: 11, h: 1.2,
        fontFace: FONT_HEAD, fontSize: 54, bold: true, color: C.white
    });
    s.addText('STM32G071RB + INA226  鋰電池量測平台', {
        x: 1.0, y: 3.2, w: 11, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 24, color: C.sky
    });

    // separator
    s.addShape('rect', {
        x: 1.0, y: 4.0, w: 1.5, h: 0.04,
        fill: { color: C.teal }, line: { color: C.teal }
    });

    // Meta block
    s.addText([
        { text: '會議代號：', options: { fontSize: 14, color: C.sky, bold: true } },
        { text: 'meeting_0506_洪大甲\n', options: { fontSize: 14, color: C.white } },
        { text: '日　　期：', options: { fontSize: 14, color: C.sky, bold: true } },
        { text: '2026-05-06\n', options: { fontSize: 14, color: C.white } },
        { text: '提 案 人：', options: { fontSize: 14, color: C.sky, bold: true } },
        { text: '洪大甲\n', options: { fontSize: 14, color: C.white } },
        { text: '對應論文：', options: { fontSize: 14, color: C.sky, bold: true } },
        { text: 'Lin et al. (2016) — Implementation of SOC and SOH Estimation for Li-ion Batteries', options: { fontSize: 14, color: C.white } }
    ], {
        x: 1.0, y: 4.3, w: 11, h: 2.0,
        fontFace: FONT_BODY, valign: 'top'
    });

    s.addText('SOC_RESEARCH', {
        x: 1.0, y: H - 0.6, w: 8, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 11, color: C.muted, charSpacing: 6
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 2 — 目的與範圍
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 2, TOTAL_PAGES, '01　目的與範圍');

    // Two columns: 目的 / 範圍
    addBlock(s, 0.55, 1.7, 6.05, 5.0,
        '測試目的',
        [
            '驗證 baa13da commit 的 MCU 韌體骨架在實機上可上電、運轉、與 INA226 通訊',
            '確認量測前端 (INA226 + Kelvin shunt) 在不依賴校正的情況下，原始讀值具備可重複性',
            '為後續動態阻抗法 SOC 與投影法 SOH 演算法提供「可信賴的量測基礎」',
            '建立可重現的測試紀錄，作為論文驗證的實驗證據'
        ],
        C.deep);

    addBlock(s, 6.78, 1.7, 6.0, 5.0,
        '本次涵蓋／不涵蓋',
        [
            '涵蓋：I2C 通訊、暫存器讀寫、量測排程、UART log 輸出、HAL clock/GPIO 設定',
            '涵蓋：演算法邊界條件白盒測試（PC 端 unit test）',
            '不涵蓋：INA226 Current_LSB 校正流程（pending，與本計畫並行）',
            '不涵蓋：量產級 EMC、機構強度、長期老化測試',
            '不涵蓋：SOC/SOH 絕對精度（取決於校正與 LUT，留待後續實驗）'
        ],
        C.teal);
}

// ──────────────────────────────────────────────────────────────
// Slide 3 — 測試對象與架構
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 3, TOTAL_PAGES, '02　測試對象與韌體架構');

    // Three layered blocks
    const layerY = 1.7;
    const layerH = 1.55;
    const gap = 0.18;

    // Layer 1: 硬體
    s.addShape('rect', {
        x: 0.55, y: layerY, w: 12.23, h: layerH,
        fill: { color: C.white }, line: { color: C.line, width: 1 }
    });
    s.addShape('rect', {
        x: 0.55, y: layerY, w: 0.12, h: layerH,
        fill: { color: C.navy }, line: { color: C.navy }
    });
    s.addText('硬體層', {
        x: 0.85, y: layerY + 0.1, w: 2.5, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.navy
    });
    s.addText('STM32G071RBTx (NUCLEO-G071RB)  ◆  INA226 模組  ◆  Rshunt 10 mΩ Kelvin  ◆  電池 DUT (18650 / LFP 單體)', {
        x: 0.85, y: layerY + 0.5, w: 11.7, h: 0.45,
        fontFace: FONT_BODY, fontSize: 13, color: C.dark
    });
    s.addText('I/O 介面：I2C1 PB8/PB9  ｜  USART2 PA2/PA3  ｜  GPIO PA5(LED) / PA10(ALERT) / PC13(BTN)', {
        x: 0.85, y: layerY + 0.95, w: 11.7, h: 0.45,
        fontFace: FONT_BODY, fontSize: 12, color: C.gray
    });

    // Layer 2: 韌體
    const y2 = layerY + layerH + gap;
    s.addShape('rect', {
        x: 0.55, y: y2, w: 12.23, h: layerH,
        fill: { color: C.white }, line: { color: C.line, width: 1 }
    });
    s.addShape('rect', {
        x: 0.55, y: y2, w: 0.12, h: layerH,
        fill: { color: C.deep }, line: { color: C.deep }
    });
    s.addText('驅動／應用層', {
        x: 0.85, y: y2 + 0.1, w: 3.0, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.deep
    });
    s.addText('Drivers/INA226：8 個公開 API（init / verify_id / write_calibration / read_bus_v / read_shunt_v / read_current / read_power）', {
        x: 0.85, y: y2 + 0.5, w: 11.7, h: 0.4,
        fontFace: FONT_BODY, fontSize: 12, color: C.dark
    });
    s.addText('App/battery_monitor：3 個 API（init / sample / get_latest），static handle 集中管理樣本快取', {
        x: 0.85, y: y2 + 0.85, w: 11.7, h: 0.4,
        fontFace: FONT_BODY, fontSize: 12, color: C.dark
    });
    s.addText('App/soc_soh_calc：2 個 API（dynamic_impedance / projection），LUT 與溫補係數待校正', {
        x: 0.85, y: y2 + 1.2, w: 11.7, h: 0.4,
        fontFace: FONT_BODY, fontSize: 12, color: C.dark
    });

    // Layer 3: 主程式
    const y3 = y2 + layerH + gap;
    s.addShape('rect', {
        x: 0.55, y: y3, w: 12.23, h: layerH,
        fill: { color: C.white }, line: { color: C.line, width: 1 }
    });
    s.addShape('rect', {
        x: 0.55, y: y3, w: 0.12, h: layerH,
        fill: { color: C.teal }, line: { color: C.teal }
    });
    s.addText('主程式', {
        x: 0.85, y: y3 + 0.1, w: 2.5, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.teal
    });
    s.addText('Core/Src/main.c — app_main()：自檢→CSV header→週期取樣 (5 Hz)→UART log→LED heartbeat', {
        x: 0.85, y: y3 + 0.5, w: 11.7, h: 0.45,
        fontFace: FONT_BODY, fontSize: 13, color: C.dark
    });
    s.addText('Core/Inc/main.h — APP_RSHUNT_OHM=0.01F  ｜  APP_CURRENT_LSB_A=0.0001525F  ｜  APP_SAMPLE_PERIOD_MS=200', {
        x: 0.85, y: y3 + 0.95, w: 11.7, h: 0.45,
        fontFace: FONT_BODY, fontSize: 12, color: C.gray, fontFace: FONT_MONO
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 4 — 測試環境設備
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 4, TOTAL_PAGES, '03　測試環境與設備清單');

    const headers = ['設備', '型號 / 規格', '用途', '取得'];
    const rows = [
        ['DC Source',     'ITECH IT6302 (3 通道)',           '提供穩定電壓 / 模擬充電電源',       '在手'],
        ['DC Load',       'ITECH IT8512A+ 300W',             '放電 / 電流脈衝 (List Mode)',       '在手'],
        ['標準 DMM',       'Keithley DMM6500 6.5 位數',        'Bus V / Shunt V ground truth',     '5/13~5/20 借用'],
        ['標準電流表',     'Fluke 87V (10 mA 解析度)',          'Current ground truth',              '在手'],
        ['Logic Analyzer','Saleae Logic Pro 8',              'I2C 訊號擷取 / 時序驗證',           '在手'],
        ['燒錄器',         'ST-Link V2 + STM32CubeProgrammer','SWD flash / RTT debug',             '在手'],
        ['UART 工具',      'Tera Term v5.x ／ Python pyserial', 'CSV 接收與解析',                    '在手'],
        ['電池 DUT',       'Samsung INR18650-25R × 3 顆',     '量測對象 (新品 + 衰退樣品)',         '採購中']
    ];

    const tableData = [
        headers.map(h => ({
            text: h,
            options: {
                bold: true, color: C.white, fill: { color: C.navy },
                fontSize: 12, fontFace: FONT_HEAD, align: 'left'
            }
        })),
        ...rows.map((row, ri) => row.map(cell => ({
            text: cell,
            options: {
                color: C.dark, fontSize: 11, fontFace: FONT_BODY,
                fill: { color: ri % 2 === 0 ? C.white : C.bg },
                align: 'left'
            }
        })))
    ];

    s.addTable(tableData, {
        x: 0.55, y: 1.7, w: 12.23,
        colW: [2.0, 3.6, 4.6, 2.03],
        rowH: 0.46,
        border: { type: 'solid', color: C.line, pt: 0.75 },
        fontFace: FONT_BODY,
        valign: 'middle'
    });

    s.addText('註：Keithley 借用窗口受限，量測精度測試 (Phase 2) 必須排在 5/13 ~ 5/20 區間完成。', {
        x: 0.55, y: 6.5, w: 12.23, h: 0.4,
        fontFace: FONT_BODY, fontSize: 11, italic: true, color: C.warn
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 5 — 測試階段總覽 (Gantt-style)
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 5, TOTAL_PAGES, '04　測試階段總覽');

    // Title above timeline
    s.addText('共四階段，與校正流程並行；每階段通過後才進入下一階段。', {
        x: 0.55, y: 1.65, w: 12.23, h: 0.4,
        fontFace: FONT_BODY, fontSize: 13, color: C.gray, italic: true
    });

    // Timeline header (weeks)
    const tlX = 2.4;
    const tlY = 2.4;
    const tlW = 10.3;
    const tlH = 4.0;
    const cols = 4;
    const colW = tlW / cols;

    // Background grid
    s.addShape('rect', {
        x: tlX, y: tlY, w: tlW, h: 0.5,
        fill: { color: C.deep }, line: { color: C.deep }
    });
    const weeks = ['W1 ｜ 5/06–5/09', 'W2 ｜ 5/12–5/16', 'W3 ｜ 5/19–5/23', 'W4 ｜ 5/26–5/30'];
    weeks.forEach((w, i) => {
        s.addText(w, {
            x: tlX + i * colW, y: tlY, w: colW, h: 0.5,
            fontFace: FONT_HEAD, fontSize: 12, bold: true, color: C.white, align: 'center', valign: 'middle'
        });
    });

    // Phase rows
    const phases = [
        { name: 'Phase 1\nBring-up & Comm', start: 0, span: 1, color: C.navy },
        { name: 'Phase 2\n量測精度',         start: 1, span: 1, color: C.deep },
        { name: 'Phase 3\n演算法驗證',        start: 2, span: 1, color: C.teal },
        { name: 'Phase 4\n系統整合',          start: 3, span: 1, color: C.warn },
        { name: '校正流程 (pending)',         start: 1, span: 2, color: C.muted }
    ];

    phases.forEach((p, i) => {
        const rowY = tlY + 0.55 + i * 0.62;
        // Row label area
        s.addShape('rect', {
            x: 0.55, y: rowY, w: tlX - 0.6, h: 0.55,
            fill: { color: C.white }, line: { color: C.line, width: 1 }
        });
        s.addText(p.name, {
            x: 0.6, y: rowY, w: tlX - 0.7, h: 0.55,
            fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.dark, valign: 'middle'
        });
        // Grid background
        for (let c = 0; c < cols; c++)
        {
            s.addShape('rect', {
                x: tlX + c * colW, y: rowY, w: colW, h: 0.55,
                fill: { color: c % 2 === 0 ? C.bg : C.white }, line: { color: C.line, width: 0.5 }
            });
        }
        // Bar
        s.addShape('roundRect', {
            x: tlX + p.start * colW + 0.1,
            y: rowY + 0.1,
            w: p.span * colW - 0.2,
            h: 0.35,
            fill: { color: p.color },
            line: { color: p.color },
            rectRadius: 0.05
        });
    });

    // Footnote
    s.addText('本日 (5/06) 起跑 Phase 1；校正流程 pending — 需確認 Keithley 借用後再排入。', {
        x: 0.55, y: 6.55, w: 12.23, h: 0.35,
        fontFace: FONT_BODY, fontSize: 11, italic: true, color: C.warn
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 6 — Phase 1: Bring-up
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 6, TOTAL_PAGES, '05　Phase 1 ｜ Bring-up 與通訊驗證');

    // Goal callout
    s.addShape('rect', {
        x: 0.55, y: 1.65, w: 12.23, h: 0.7,
        fill: { color: C.navy }, line: { color: C.navy }
    });
    s.addText('目標：韌體可上電、SystemClock 正確、INA226 通訊成功、UART log 可讀、LED 心跳正常', {
        x: 0.75, y: 1.7, w: 11.8, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.white, valign: 'middle'
    });

    // Test cases table
    const tHeader = ['編號', '測項', '驗證方法', '通過條件'];
    const tRows = [
        ['T1.1', 'SWD 連線 / Erase / Flash 可重複', 'STM32CubeProgrammer 連續 5 次 erase + flash', '5/5 通過、無 timeout'],
        ['T1.2', 'SystemClock 64 MHz 確認',       'MCO 接示波器，量測 8 MHz (÷8 後)',         '7.95 ~ 8.05 MHz'],
        ['T1.3', 'INA226 Manufacturer / Die ID',   '韌體啟動讀 0xFE / 0xFF，UART log 印出',     'MFG=0x5449, Die=0x2260'],
        ['T1.4', 'USART2 CSV header 輸出',         '115200/8N1 接收 PC 端 Tera Term',           '正確收到 ts_ms,bus_v_mv,...'],
        ['T1.5', 'LED 心跳 (PA5)',                 '示波器或目視',                              '5 Hz ± 5 % 閃爍']
    ];
    const tableData = [
        tHeader.map(h => ({
            text: h,
            options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 12, fontFace: FONT_HEAD, align: 'left' }
        })),
        ...tRows.map((row, ri) => row.map((cell, ci) => ({
            text: cell,
            options: {
                color: ci === 0 ? C.deep : C.dark,
                bold: ci === 0,
                fontSize: 11, fontFace: ci === 0 ? FONT_MONO : FONT_BODY,
                fill: { color: ri % 2 === 0 ? C.white : C.bg },
                align: 'left'
            }
        })))
    ];

    s.addTable(tableData, {
        x: 0.55, y: 2.55, w: 12.23,
        colW: [1.1, 3.3, 4.83, 3.0],
        rowH: 0.5,
        border: { type: 'solid', color: C.line, pt: 0.75 },
        valign: 'middle'
    });

    // Pass criteria
    s.addShape('rect', {
        x: 0.55, y: 6.4, w: 12.23, h: 0.55,
        fill: { color: C.ok }, line: { color: C.ok }
    });
    s.addText('Phase 1 通過條件：T1.1 ~ T1.5 全部 PASS；任一 FAIL 須回頭修正後重測，不得跳階段', {
        x: 0.75, y: 6.42, w: 11.8, h: 0.5,
        fontFace: FONT_HEAD, fontSize: 12, bold: true, color: C.white, valign: 'middle'
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 7 — Phase 2: 量測精度
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 7, TOTAL_PAGES, '06　Phase 2 ｜ 量測精度驗證');

    s.addShape('rect', {
        x: 0.55, y: 1.65, w: 12.23, h: 0.7,
        fill: { color: C.deep }, line: { color: C.deep }
    });
    s.addText('目標：INA226 讀值與 Keithley DMM6500 ground truth 之相對誤差 < 1 % (Bus / Shunt V)', {
        x: 0.75, y: 1.7, w: 11.8, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.white, valign: 'middle'
    });

    const tHeader = ['編號', '測項', '測試條件', '取樣點', '通過條件'];
    const tRows = [
        ['T2.1', 'Bus V 線性度',     'IT6302 注入 0 ~ 5 V，0.5 V step',  '11 點 × 3 次',  '回歸線 R² > 0.999，最大誤差 < 1 %'],
        ['T2.2', 'Shunt V 線性度',   'IT6302 + 分壓電路 ±50 mV',          '21 點 × 3 次',  '最大誤差 < 1 %（pre-CAL）'],
        ['T2.3', 'Current 線性度 *', 'IT8512A+ CC 模式 0 ~ 5 A',          '11 點 × 3 次',  '記錄供校正擬合 (本階段不收驗)'],
        ['T2.4', '取樣週期穩定度',     'Logic Analyzer 量 SDA toggle 間距',  '連續 1000 次',  '200 ms ± 1 %'],
        ['T2.5', 'I2C 連續讀取穩定',  '韌體 loop 連續讀取',                '10 000 次',     '0 NACK / 0 timeout']
    ];

    const tableData = [
        tHeader.map(h => ({
            text: h,
            options: { bold: true, color: C.white, fill: { color: C.deep }, fontSize: 11, fontFace: FONT_HEAD, align: 'left' }
        })),
        ...tRows.map((row, ri) => row.map((cell, ci) => ({
            text: cell,
            options: {
                color: ci === 0 ? C.deep : C.dark,
                bold: ci === 0,
                fontSize: 10.5, fontFace: ci === 0 ? FONT_MONO : FONT_BODY,
                fill: { color: ri % 2 === 0 ? C.white : C.bg },
                align: 'left'
            }
        })))
    ];

    s.addTable(tableData, {
        x: 0.55, y: 2.55, w: 12.23,
        colW: [1.1, 2.4, 3.5, 1.83, 3.4],
        rowH: 0.55,
        border: { type: 'solid', color: C.line, pt: 0.75 },
        valign: 'middle'
    });

    s.addText('* T2.3 標記為「校正依賴」：於校正流程啟動前僅記錄資料，不作為通過依據', {
        x: 0.55, y: 6.0, w: 12.23, h: 0.35,
        fontFace: FONT_BODY, fontSize: 11, italic: true, color: C.warn
    });

    s.addShape('rect', {
        x: 0.55, y: 6.4, w: 12.23, h: 0.55,
        fill: { color: C.ok }, line: { color: C.ok }
    });
    s.addText('Phase 2 通過條件：T2.1 / T2.2 / T2.4 / T2.5 全 PASS；T2.3 收集供校正用', {
        x: 0.75, y: 6.42, w: 11.8, h: 0.5,
        fontFace: FONT_HEAD, fontSize: 12, bold: true, color: C.white, valign: 'middle'
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 8 — Phase 3: 演算法驗證 (白盒 unit test)
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 8, TOTAL_PAGES, '07　Phase 3 ｜ 演算法白盒驗證');

    s.addShape('rect', {
        x: 0.55, y: 1.65, w: 12.23, h: 0.7,
        fill: { color: C.teal }, line: { color: C.teal }
    });
    s.addText('目標：在 PC 端以 unit test 餵入已知測資，驗證 SOC/SOH 計算邏輯與邊界處理', {
        x: 0.75, y: 1.7, w: 11.8, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.white, valign: 'middle'
    });

    // Two cards: dynamic impedance / projection
    addBlock(s, 0.55, 2.55, 6.05, 4.0,
        'T3.1 動態阻抗法 (soc_calc_dynamic_impedance)',
        [
            '邊界 1：sample_before == NULL → 回 false',
            '邊界 2：sample_after->is_valid == false → 回 false',
            '邊界 3：|ΔI| < 1.0 mA → 回 false（避免除零）',
            '正常 1：ΔV=10 mV, ΔI=1000 mA → z_mohm = 10.000',
            '正常 2：ΔV=-25 mV, ΔI=-2500 mA → z_mohm = 10.000',
            'TODO（校正後）：Z → SOC LUT 查表結果驗證'
        ],
        C.teal);

    addBlock(s, 6.78, 2.55, 6.0, 4.0,
        'T3.2 投影法 (soh_calc_projection)',
        [
            '邊界 1：nominal_capacity_mah <= 0 → 回 false',
            '邊界 2：cumulative_charge_mah < 0 → ratio clamp 至 0',
            '邊界 3：cumulative_charge_mah > nominal → ratio clamp 至 1',
            '正常 1：cum=2500, nominal=2500 → SOH = 100.0 %',
            '正常 2：cum=2125, nominal=2500 → SOH = 85.0 %',
            'TODO（校正後）：溫補係數 temperature_c 影響驗證'
        ],
        C.deep);

    s.addText('工具：在 PC 端以 GCC + CUnit 編譯 soc_soh_calc.c (link 一個 stub HAL)；CI 可放入後續 GitHub Actions', {
        x: 0.55, y: 6.6, w: 12.23, h: 0.4,
        fontFace: FONT_BODY, fontSize: 11, italic: true, color: C.gray
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 9 — Phase 4: 系統整合
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 9, TOTAL_PAGES, '08　Phase 4 ｜ 系統整合與長時間穩定性');

    s.addShape('rect', {
        x: 0.55, y: 1.65, w: 12.23, h: 0.7,
        fill: { color: C.warn }, line: { color: C.warn }
    });
    s.addText('目標：模擬實際充放電場景，驗證 12 小時連續運轉、ALERT 中斷、按鈕觸發功能', {
        x: 0.75, y: 1.7, w: 11.8, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.white, valign: 'middle'
    });

    const tHeader = ['編號', '測項', '測試流程', '通過條件'];
    const tRows = [
        ['T4.1', '完整充放電循環',   'IT6302 CC-CV 充至 4.2 V → IT8512A+ CC 1A 放至 3.0 V，全程 log',  '電量平衡誤差 < 5 %'],
        ['T4.2', '12 小時連續運轉', '韌體 5 Hz 取樣連跑 12 hr，stack 高水位回讀',                       '不重啟、stack 餘裕 > 30 %'],
        ['T4.3', 'ALERT 中斷',     'IT8512A+ 突放 6 A 觸發 INA226 over-current',                      'EXTI ISR 在 < 100 µs 內觸發'],
        ['T4.4', '按鈕單次量測標記', '按下 PC13 USER_BTN，CSV log 出現 mark 欄位',                      'log 對應行可被解析'],
        ['T4.5', '12 hr CSV 解析',  'Python pandas 讀檔，畫 V/I/P 曲線',                              '無丟行 / 時間戳單調遞增']
    ];
    const tableData = [
        tHeader.map(h => ({
            text: h,
            options: { bold: true, color: C.white, fill: { color: C.warn }, fontSize: 12, fontFace: FONT_HEAD, align: 'left' }
        })),
        ...tRows.map((row, ri) => row.map((cell, ci) => ({
            text: cell,
            options: {
                color: ci === 0 ? C.warn : C.dark,
                bold: ci === 0,
                fontSize: 11, fontFace: ci === 0 ? FONT_MONO : FONT_BODY,
                fill: { color: ri % 2 === 0 ? C.white : C.bg },
                align: 'left'
            }
        })))
    ];

    s.addTable(tableData, {
        x: 0.55, y: 2.55, w: 12.23,
        colW: [1.1, 2.4, 5.3, 3.43],
        rowH: 0.55,
        border: { type: 'solid', color: C.line, pt: 0.75 },
        valign: 'middle'
    });

    s.addShape('rect', {
        x: 0.55, y: 6.4, w: 12.23, h: 0.55,
        fill: { color: C.ok }, line: { color: C.ok }
    });
    s.addText('Phase 4 通過條件：T4.1 / T4.2 / T4.5 全 PASS；T4.3、T4.4 為 nice-to-have', {
        x: 0.75, y: 6.42, w: 11.8, h: 0.5,
        fontFace: FONT_HEAD, fontSize: 12, bold: true, color: C.white, valign: 'middle'
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 10 — 驗收條件矩陣
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 10, TOTAL_PAGES, '09　驗收條件矩陣');

    const tHeader = ['階段', 'Must Pass', 'Nice to Have', '校正依賴', '預估完成'];
    const tRows = [
        ['Phase 1 ｜ Bring-up',   'T1.1 / 1.2 / 1.3 / 1.4 / 1.5', '—',                     '否',  '5/09'],
        ['Phase 2 ｜ 量測精度',    'T2.1 / 2.2 / 2.4 / 2.5',       'T2.3 (校正後重收)',     '部分 (T2.3)',  '5/16'],
        ['Phase 3 ｜ 演算法',     'T3.1 / 3.2 (邊界 + 已知測資)',  '—',                     '否',  '5/23'],
        ['Phase 4 ｜ 系統整合',   'T4.1 / 4.2 / 4.5',             'T4.3 / 4.4',            '否',  '5/30'],
        ['校正流程 (pending)',    '—',                            '完整 LUT + 溫補擬合',     '是 (依此而生)', 'TBD']
    ];
    const tableData = [
        tHeader.map(h => ({
            text: h,
            options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 12, fontFace: FONT_HEAD, align: 'left' }
        })),
        ...tRows.map((row, ri) => row.map((cell, ci) => ({
            text: cell,
            options: {
                color: ci === 0 ? C.deep : C.dark,
                bold: ci === 0,
                fontSize: 11, fontFace: FONT_BODY,
                fill: { color: ri % 2 === 0 ? C.white : C.bg },
                align: 'left'
            }
        })))
    ];

    s.addTable(tableData, {
        x: 0.55, y: 1.7, w: 12.23,
        colW: [3.0, 3.5, 2.7, 1.6, 1.43],
        rowH: 0.7,
        border: { type: 'solid', color: C.line, pt: 0.75 },
        valign: 'middle'
    });

    // Summary callout
    s.addShape('rect', {
        x: 0.55, y: 5.85, w: 12.23, h: 1.1,
        fill: { color: C.white }, line: { color: C.deep, width: 1.5 }
    });
    s.addText('總結驗收：四階段 Must Pass 全通過，視為韌體骨架達到「可進入校正流程」之里程碑。', {
        x: 0.85, y: 5.95, w: 11.7, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.deep
    });
    s.addText('每筆測試需附：時間、設備序號、原始 log 檔、判讀人；FAIL 須記 root cause 與修正 commit。', {
        x: 0.85, y: 6.4, w: 11.7, h: 0.5,
        fontFace: FONT_BODY, fontSize: 11, color: C.gray
    });
}

// ──────────────────────────────────────────────────────────────
// Slide 11 — 風險、限制、下一步
// ──────────────────────────────────────────────────────────────
{
    const s = pptx.addSlide();
    addPageDecor(s, 11, TOTAL_PAGES, '10　風險、限制、下一步');

    addBlock(s, 0.55, 1.7, 4.05, 5.0,
        '風險',
        [
            'INA226 模組來源未驗證，需採購正廠 (Adafruit / TI EVM) 以排除假晶片',
            'Kelvin shunt 走線阻抗 (> 1 mΩ) 會造成系統性誤差，需 4-wire layout',
            'Keithley DMM6500 借用窗口僅 5/13–5/20，逾期將拖延 Phase 2',
            '長時間 (12 hr) 測試可能因 USART log buffer overflow 造成丟行'
        ],
        C.danger);

    addBlock(s, 4.78, 1.7, 4.05, 5.0,
        '限制',
        [
            '校正流程 pending：Phase 2 T2.3 與 SOC 絕對精度暫不收驗',
            '動態阻抗 SOC 對應表 (Z-SOC LUT) 未建立，Phase 3 僅驗算式',
            'STM32 stack 設定為 0x400 (1 KB)，遞迴或大型 buffer 不適用',
            '本計畫未涵蓋多顆電池串並聯場景 (留待後續延伸)'
        ],
        C.warn);

    addBlock(s, 9.01, 1.7, 3.79, 5.0,
        '下一步 (本週)',
        [
            '5/07 ｜ CubeMX 生成 HAL skeleton，將 App / Drivers/INA226 併入 Makefile build',
            '5/08 ｜ 採購 INA226 模組 + 10 mΩ Kelvin shunt 樣品',
            '5/09 ｜ 啟動 Phase 1 實機測試 (T1.1 ~ T1.5)',
            '5/10 ｜ 整理 Phase 1 結果，更新 CLAUDE.md 與會議簡報'
        ],
        C.ok);
}

// ───────────── Save ─────────────
const outPath = path.resolve('DOC/會議紀錄/meeting_0506_洪大甲.pptx');
pptx.writeFile({ fileName: outPath })
    .then(p => { console.log('OK:', p); })
    .catch(e => { console.error('ERR:', e); process.exit(1); });
