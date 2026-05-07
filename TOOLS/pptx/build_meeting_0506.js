// build_meeting_0506.js
// 重新產生 meeting_0506_洪大甲.pptx (9 頁版)
// 變更摘要：
//   - Phase 1 改名為「MCU 通訊測試」
//   - 拿掉 Phase 2 (量測精度驗證)
//   - Phase 3 改方塊圖 (演算法單元測試)
//   - Phase 4 改流程圖 (系統整合, Pi orchestrated)
//   - 驗收矩陣改「預估時間表」, 規劃 2 週內完成
//   - 加入 Raspberry Pi 5 + USB-to-TTL UART × 3 作為儀器/MCU orchestrator
//   - 拿掉 Keithley DMM6500、Tera Term、ALERT/按鈕測試、到貨清點

const path = require("path");
require("module").Module._initPaths();
const PptxGenJS = require(path.join(
  process.env.APPDATA,
  "npm",
  "node_modules",
  "pptxgenjs"
));

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE"; // 13.33" x 7.5"
pres.author = "洪大甲";
pres.title = "STM32G071 + INA226 韌體驗證測試計畫";
pres.subject = "meeting_0506_洪大甲";

// ===== 色票 (Midnight Executive) =====
const NAVY = "1E2761";
const NAVY_DEEP = "0F1638";
const ICE = "CADCFC";
const WHITE = "FFFFFF";
const ACCENT = "FFB400"; // 金色 accent
const MUTED = "64748B"; // 註解灰
const LIGHT_BG = "F8FAFC";
const DARK_TEXT = "0F172A";
const SOFT_LINE = "E2E8F0";
const PHASE1_COLOR = "0E7490"; // 青藍 (Phase 1)
const PHASE2_COLOR = "7C3AED"; // 紫 (Phase 2)
const PHASE3_COLOR = "DC2626"; // 紅 (Phase 3)

// ===== 字型 =====
const FONT_HEAD = "Microsoft JhengHei";
const FONT_BODY = "Microsoft JhengHei";

// ===== 共用 helper =====
function addPageHeader(slide, num, title, accentColor) {
  // 上方深色 header bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0,
    y: 0,
    w: 13.33,
    h: 0.85,
    fill: { color: NAVY },
    line: { color: NAVY, width: 0 },
  });
  // 編號方塊
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0,
    y: 0,
    w: 1.0,
    h: 0.85,
    fill: { color: accentColor || ACCENT },
    line: { color: accentColor || ACCENT, width: 0 },
  });
  slide.addText(String(num).padStart(2, "0"), {
    x: 0,
    y: 0,
    w: 1.0,
    h: 0.85,
    fontSize: 28,
    fontFace: FONT_HEAD,
    color: WHITE,
    bold: true,
    align: "center",
    valign: "middle",
    margin: 0,
  });
  // 標題
  slide.addText(title, {
    x: 1.2,
    y: 0,
    w: 11.5,
    h: 0.85,
    fontSize: 22,
    fontFace: FONT_HEAD,
    color: WHITE,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
}

function addPageFooter(slide, idx, total) {
  // 底線
  slide.addShape(pres.shapes.LINE, {
    x: 0.5,
    y: 7.05,
    w: 12.33,
    h: 0,
    line: { color: SOFT_LINE, width: 1 },
  });
  slide.addText("SOC_RESEARCH  |  meeting_0506_洪大甲", {
    x: 0.5,
    y: 7.1,
    w: 8,
    h: 0.35,
    fontSize: 10,
    fontFace: FONT_BODY,
    color: MUTED,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  slide.addText(`${idx} / ${total}`, {
    x: 11.5,
    y: 7.1,
    w: 1.33,
    h: 0.35,
    fontSize: 10,
    fontFace: FONT_BODY,
    color: MUTED,
    align: "right",
    valign: "middle",
    margin: 0,
  });
}

const TOTAL = 9;

// ============================================================
// Slide 1 - 封面
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // 大色塊裝飾
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0,
    y: 0,
    w: 0.4,
    h: 7.5,
    fill: { color: ACCENT },
    line: { color: ACCENT, width: 0 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 11.5,
    y: 0,
    w: 1.83,
    h: 7.5,
    fill: { color: NAVY_DEEP },
    line: { color: NAVY_DEEP, width: 0 },
  });

  // SOC_RESEARCH (右上)
  s.addText("SOC_RESEARCH", {
    x: 11.4,
    y: 0.4,
    w: 1.93,
    h: 0.4,
    fontSize: 10,
    fontFace: FONT_HEAD,
    color: ICE,
    bold: true,
    charSpacing: 2,
    align: "center",
    valign: "middle",
    margin: 0,
  });

  // TEST PLAN
  s.addText("TEST PLAN", {
    x: 1.0,
    y: 1.4,
    w: 10,
    h: 0.7,
    fontSize: 36,
    fontFace: FONT_HEAD,
    color: ACCENT,
    bold: true,
    charSpacing: 8,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 主標題
  s.addText("韌體驗證測試計畫", {
    x: 1.0,
    y: 2.2,
    w: 10,
    h: 1.0,
    fontSize: 48,
    fontFace: FONT_HEAD,
    color: WHITE,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 副標題
  s.addText("STM32G071RB + INA226  鋰電池 SOC / SOH MCU 驗證", {
    x: 1.0,
    y: 3.4,
    w: 10,
    h: 0.6,
    fontSize: 22,
    fontFace: FONT_BODY,
    color: ICE,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 分隔線
  s.addShape(pres.shapes.LINE, {
    x: 1.0,
    y: 4.3,
    w: 6,
    h: 0,
    line: { color: ACCENT, width: 2 },
  });

  // Meta
  s.addText(
    [
      {
        text: "會議代號 : ",
        options: { color: MUTED, bold: false },
      },
      {
        text: "meeting_0506_洪大甲",
        options: { color: WHITE, bold: true, breakLine: true },
      },
      {
        text: "日　　期 : ",
        options: { color: MUTED, bold: false },
      },
      {
        text: "2026-05-06",
        options: { color: WHITE, bold: true, breakLine: true },
      },
      {
        text: "報 告 人 : ",
        options: { color: MUTED, bold: false },
      },
      {
        text: "洪大甲",
        options: { color: WHITE, bold: true, breakLine: true },
      },
      {
        text: "參考論文 : ",
        options: { color: MUTED, bold: false },
      },
      {
        text:
          "Lin et al. (2016) — Implementation of SOC and SOH Estimation for Li-ion Batteries",
        options: { color: WHITE, bold: false },
      },
    ],
    {
      x: 1.0,
      y: 4.6,
      w: 10,
      h: 2.0,
      fontSize: 14,
      fontFace: FONT_BODY,
      align: "left",
      valign: "top",
      margin: 0,
      paraSpaceAfter: 6,
    }
  );

  // 底部 tag
  s.addText("Phase 1  ▸  Phase 2  ▸  Phase 3   |   兩週完成 (5/06 — 5/19)", {
    x: 1.0,
    y: 6.7,
    w: 10,
    h: 0.4,
    fontSize: 12,
    fontFace: FONT_HEAD,
    color: ICE,
    bold: true,
    charSpacing: 3,
    align: "left",
    valign: "middle",
    margin: 0,
  });
}

// ============================================================
// Slide 2 - 目的與範圍
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 1, "目的與範圍", NAVY_DEEP);
  addPageFooter(s, 2, TOTAL);

  // 上方說明
  s.addText("以最小可行原型 (MVP) 驗證 MCU + INA226 採樣鏈與 SOC/SOH 演算法骨架；兩週內完成、可重現、可量化。", {
    x: 0.5,
    y: 1.05,
    w: 12.33,
    h: 0.5,
    fontSize: 14,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 兩欄: 範圍包含 / 範圍排除
  const COL_W = 6.0;
  const COL_Y = 1.7;
  const COL_H = 5.1;

  // 左欄：範圍包含
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: COL_Y,
    w: COL_W,
    h: COL_H,
    fill: { color: WHITE },
    line: { color: SOFT_LINE, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: COL_Y,
    w: 0.12,
    h: COL_H,
    fill: { color: PHASE1_COLOR },
    line: { color: PHASE1_COLOR, width: 0 },
  });
  s.addText("範圍包含", {
    x: 0.85,
    y: COL_Y + 0.15,
    w: COL_W - 0.5,
    h: 0.4,
    fontSize: 18,
    fontFace: FONT_HEAD,
    color: PHASE1_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  s.addText(
    [
      { text: "MCU 硬體驗證：時脈、I2C、UART、GPIO 通訊", options: { bullet: { code: "25A0" }, breakLine: true } },
      { text: "INA226 採樣鏈：Bus V、Shunt V、計算 Current", options: { bullet: { code: "25A0" }, breakLine: true } },
      { text: "演算法骨架：動態阻抗法 SOC、投影法 SOH 可呼叫之介面", options: { bullet: { code: "25A0" }, breakLine: true } },
      { text: "PC 端 unit test：邊界條件 + 標稱值通過", options: { bullet: { code: "25A0" }, breakLine: true } },
      { text: "Raspberry Pi 5 編排：自動充→放→List Mode→long-run", options: { bullet: { code: "25A0" }, breakLine: true } },
      { text: "Pi 同步收儀器 readback 與 MCU CSV，產出時間對齊 log", options: { bullet: { code: "25A0" } } },
    ],
    {
      x: 0.85,
      y: COL_Y + 0.6,
      w: COL_W - 0.5,
      h: COL_H - 0.7,
      fontSize: 13,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      paraSpaceAfter: 8,
      valign: "top",
      margin: 0,
    }
  );

  // 右欄：範圍排除
  const RX = 6.83;
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX,
    y: COL_Y,
    w: COL_W,
    h: COL_H,
    fill: { color: WHITE },
    line: { color: SOFT_LINE, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX,
    y: COL_Y,
    w: 0.12,
    h: COL_H,
    fill: { color: MUTED },
    line: { color: MUTED, width: 0 },
  });
  s.addText("範圍排除", {
    x: RX + 0.35,
    y: COL_Y + 0.15,
    w: COL_W - 0.5,
    h: 0.4,
    fontSize: 18,
    fontFace: FONT_HEAD,
    color: MUTED,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  s.addText(
    [
      { text: "INA226 Current_LSB 校正流程 (待定，另行排入)", options: { bullet: { code: "25A1" }, breakLine: true } },
      { text: "PCBA 設計、EMC 認證、機構強度", options: { bullet: { code: "25A1" }, breakLine: true } },
      { text: "電池模型參數化 (溫度補償、老化曲線完整建模)", options: { bullet: { code: "25A1" }, breakLine: true } },
      { text: "SOC ↔ Z 阻抗 LUT 完整建表 (僅預留介面)", options: { bullet: { code: "25A1" }, breakLine: true } },
      { text: "OTA 韌體升級、產品化 UI", options: { bullet: { code: "25A1" } } },
    ],
    {
      x: RX + 0.35,
      y: COL_Y + 0.6,
      w: COL_W - 0.5,
      h: COL_H - 0.7,
      fontSize: 13,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      paraSpaceAfter: 8,
      valign: "top",
      margin: 0,
    }
  );
}

// ============================================================
// Slide 3 - 測試平台架構
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 2, "測試平台架構", NAVY_DEEP);
  addPageFooter(s, 3, TOTAL);

  // 上方說明
  s.addText("Raspberry Pi 5 為總控制端 (orchestrator)，透過 USB-to-TTL UART 同時控儀器與收 MCU log。", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // === 拓樸圖 ===
  // Pi 5 (top center)
  const PI_X = 5.4;
  const PI_Y = 1.6;
  const PI_W = 2.5;
  const PI_H = 0.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: PI_X,
    y: PI_Y,
    w: PI_W,
    h: PI_H,
    fill: { color: NAVY },
    line: { color: NAVY, width: 0 },
    rectRadius: 0.08,
  });
  s.addText(
    [
      { text: "Raspberry Pi 5", options: { bold: true, fontSize: 14, color: WHITE, breakLine: true } },
      { text: "test_runner.py", options: { fontSize: 11, color: ICE } },
    ],
    {
      x: PI_X,
      y: PI_Y,
      w: PI_W,
      h: PI_H,
      fontFace: FONT_BODY,
      align: "center",
      valign: "middle",
      margin: 0,
    }
  );

  // 三條 USB-to-TTL adapter 中介盒
  const ADAPT_Y = 3.05;
  const ADAPT_W = 1.7;
  const ADAPT_H = 0.55;
  const adapters = [
    { x: 1.4, label: "USB-TTL #1" },
    { x: 5.8, label: "USB-TTL #2" },
    { x: 10.2, label: "USB-TTL #3" },
  ];
  adapters.forEach((a) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: a.x,
      y: ADAPT_Y,
      w: ADAPT_W,
      h: ADAPT_H,
      fill: { color: ICE },
      line: { color: NAVY, width: 1 },
      rectRadius: 0.06,
    });
    s.addText(a.label, {
      x: a.x,
      y: ADAPT_Y,
      w: ADAPT_W,
      h: ADAPT_H,
      fontSize: 11,
      fontFace: FONT_BODY,
      color: NAVY,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
  });

  // Pi → Adapters 連線 (T-shape)
  // 主幹
  s.addShape(pres.shapes.LINE, {
    x: PI_X + PI_W / 2,
    y: PI_Y + PI_H,
    w: 0,
    h: 0.25,
    line: { color: NAVY, width: 2 },
  });
  // 橫線跨三個 adapter
  s.addShape(pres.shapes.LINE, {
    x: 1.4 + ADAPT_W / 2,
    y: PI_Y + PI_H + 0.25,
    w: (10.2 + ADAPT_W / 2) - (1.4 + ADAPT_W / 2),
    h: 0,
    line: { color: NAVY, width: 2 },
  });
  // 三條垂直到 adapter
  adapters.forEach((a) => {
    s.addShape(pres.shapes.LINE, {
      x: a.x + ADAPT_W / 2,
      y: PI_Y + PI_H + 0.25,
      w: 0,
      h: ADAPT_Y - (PI_Y + PI_H + 0.25),
      line: { color: NAVY, width: 2 },
    });
  });

  // USB 標籤
  s.addText("USB ×3", {
    x: 5.0,
    y: PI_Y + PI_H + 0.05,
    w: 1.5,
    h: 0.25,
    fontSize: 9,
    fontFace: FONT_BODY,
    color: MUTED,
    italic: true,
    align: "center",
    valign: "middle",
    margin: 0,
  });

  // 三個下方裝置 (儀器 + MCU)
  const DEV_Y = 4.3;
  const DEV_W = 2.7;
  const DEV_H = 1.5;
  const devs = [
    {
      x: 0.9,
      title: "IT6302",
      sub: "DC Source (3 ch)",
      role: "Pi 控充電",
      color: PHASE1_COLOR,
    },
    {
      x: 5.3,
      title: "STM32G071RB",
      sub: "USART2 CSV log",
      role: "Pi 收 MCU 數據",
      color: PHASE2_COLOR,
    },
    {
      x: 9.7,
      title: "IT8512A+",
      sub: "DC Load 300W",
      role: "Pi 控放電 + List Mode",
      color: PHASE3_COLOR,
    },
  ];
  devs.forEach((d) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: d.x,
      y: DEV_Y,
      w: DEV_W,
      h: DEV_H,
      fill: { color: WHITE },
      line: { color: d.color, width: 2 },
      rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: d.x,
      y: DEV_Y,
      w: DEV_W,
      h: 0.45,
      fill: { color: d.color },
      line: { color: d.color, width: 0 },
    });
    s.addText(d.title, {
      x: d.x,
      y: DEV_Y,
      w: DEV_W,
      h: 0.45,
      fontSize: 14,
      fontFace: FONT_HEAD,
      color: WHITE,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
    s.addText(d.sub, {
      x: d.x + 0.1,
      y: DEV_Y + 0.5,
      w: DEV_W - 0.2,
      h: 0.4,
      fontSize: 12,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
    s.addText(d.role, {
      x: d.x + 0.1,
      y: DEV_Y + 0.95,
      w: DEV_W - 0.2,
      h: 0.45,
      fontSize: 11,
      fontFace: FONT_BODY,
      color: MUTED,
      italic: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
  });

  // Adapter → Device 連線 (TTL 標示)
  adapters.forEach((a, i) => {
    const dev = devs[i];
    s.addShape(pres.shapes.LINE, {
      x: a.x + ADAPT_W / 2,
      y: ADAPT_Y + ADAPT_H,
      w: dev.x + DEV_W / 2 - (a.x + ADAPT_W / 2),
      h: DEV_Y - (ADAPT_Y + ADAPT_H),
      line: { color: NAVY, width: 1.5, dashType: "dash" },
    });
  });
  s.addText("TTL UART  3.3V / 115200 / 8N1", {
    x: 0.5,
    y: 4.05,
    w: 12.33,
    h: 0.2,
    fontSize: 9,
    fontFace: FONT_BODY,
    color: MUTED,
    italic: true,
    align: "center",
    valign: "middle",
    margin: 0,
  });

  // 電池與 INA226 (底部)
  const BAT_Y = 6.05;
  const BAT_X = 4.4;
  const BAT_W = 4.5;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: BAT_X,
    y: BAT_Y,
    w: BAT_W,
    h: 0.7,
    fill: { color: ACCENT },
    line: { color: ACCENT, width: 0 },
    rectRadius: 0.06,
  });
  s.addText("INR18650-25R  +  INA226 / 10 mΩ Kelvin shunt", {
    x: BAT_X,
    y: BAT_Y,
    w: BAT_W,
    h: 0.7,
    fontSize: 12,
    fontFace: FONT_BODY,
    color: NAVY_DEEP,
    bold: true,
    align: "center",
    valign: "middle",
    margin: 0,
  });

  // 接到 IT6302 / IT8512A+ 的電源線 (粗線)
  // helper: 從兩個 (x,y) 點畫線, 自動處理 flipV (避免 negative dim)
  function lineFromPts(x1, y1, x2, y2, color, width, dash) {
    const x = Math.min(x1, x2);
    const y = Math.min(y1, y2);
    const w = Math.abs(x2 - x1);
    const h = Math.abs(y2 - y1);
    const flipV = (y1 > y2) ^ (x1 > x2);  // 是否要翻轉
    const opts = {
      x, y, w, h,
      line: { color, width, ...(dash ? { dashType: dash } : {}) },
    };
    if (flipV) opts.flipV = true;
    s.addShape(pres.shapes.LINE, opts);
  }
  // IT6302 right → BAT left
  lineFromPts(
    devs[0].x + DEV_W, DEV_Y + DEV_H / 2,
    BAT_X, BAT_Y + 0.35,
    PHASE1_COLOR, 3
  );
  // BAT right → IT8512A+ left
  lineFromPts(
    BAT_X + BAT_W, BAT_Y + 0.35,
    devs[2].x, DEV_Y + DEV_H / 2,
    PHASE3_COLOR, 3
  );
  // MCU 到 INA226 (I2C 虛線)
  s.addShape(pres.shapes.LINE, {
    x: devs[1].x + DEV_W / 2,
    y: DEV_Y + DEV_H,
    w: 0,
    h: BAT_Y - (DEV_Y + DEV_H),
    line: { color: PHASE2_COLOR, width: 2, dashType: "dash" },
  });
  s.addText("I2C", {
    x: devs[1].x + DEV_W / 2 + 0.08,
    y: DEV_Y + DEV_H + 0.05,
    w: 0.45,
    h: 0.22,
    fontSize: 9,
    fontFace: FONT_BODY,
    color: PHASE2_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
}

// ============================================================
// Slide 4 - 設備清單
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 3, "測試環境與設備清單", NAVY_DEEP);
  addPageFooter(s, 4, TOTAL);

  s.addText("既有設備已就位；★ 為本次新增 (取代舊驗證流程的 Tera Term + Keithley)", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 12,
    fontFace: FONT_BODY,
    color: MUTED,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  const tableHead = [
    {
      text: "類別",
      options: { fill: { color: NAVY }, color: WHITE, bold: true, align: "center", valign: "middle" },
    },
    {
      text: "型號 / 規格",
      options: { fill: { color: NAVY }, color: WHITE, bold: true, align: "center", valign: "middle" },
    },
    {
      text: "用途",
      options: { fill: { color: NAVY }, color: WHITE, bold: true, align: "center", valign: "middle" },
    },
    {
      text: "狀態",
      options: { fill: { color: NAVY }, color: WHITE, bold: true, align: "center", valign: "middle" },
    },
  ];
  const rowOpt = (bg) => ({ fill: { color: bg }, valign: "middle", color: DARK_TEXT });
  const newOpt = (bg) => ({
    fill: { color: bg },
    valign: "middle",
    color: PHASE3_COLOR,
    bold: true,
  });
  const rows = [
    [
      { text: "MCU 主控", options: rowOpt(WHITE) },
      { text: "STM32G071RB (NUCLEO-G071RB)", options: rowOpt(WHITE) },
      { text: "採樣調度、I2C、UART、SOC/SOH 演算法", options: rowOpt(WHITE) },
      { text: "在手", options: rowOpt(WHITE) },
    ],
    [
      { text: "量測 IC", options: rowOpt(LIGHT_BG) },
      { text: "INA226 + Kelvin shunt 10 mΩ", options: rowOpt(LIGHT_BG) },
      { text: "Bus V、Shunt V → 電流推算 (±8.19A 量程)", options: rowOpt(LIGHT_BG) },
      { text: "在手", options: rowOpt(LIGHT_BG) },
    ],
    [
      { text: "DC Source", options: rowOpt(WHITE) },
      { text: "ITECH IT6302 (3 ch)", options: rowOpt(WHITE) },
      { text: "充電 CC-CV (Pi 控)", options: rowOpt(WHITE) },
      { text: "在手", options: rowOpt(WHITE) },
    ],
    [
      { text: "DC Load", options: rowOpt(LIGHT_BG) },
      { text: "ITECH IT8512A+ 300W", options: rowOpt(LIGHT_BG) },
      { text: "放電 CC、List Mode 動態階躍 (Pi 控)", options: rowOpt(LIGHT_BG) },
      { text: "在手", options: rowOpt(LIGHT_BG) },
    ],
    [
      { text: "★ 控制端", options: newOpt(WHITE) },
      { text: "Raspberry Pi 5 (4GB)", options: newOpt(WHITE) },
      { text: "test_runner.py 編排充放電 + 收 log", options: newOpt(WHITE) },
      { text: "在手", options: newOpt(WHITE) },
    ],
    [
      { text: "★ 通訊轉接", options: newOpt(LIGHT_BG) },
      { text: "USB-to-TTL UART × 3 (CP2102 / FT232)", options: newOpt(LIGHT_BG) },
      { text: "Pi → IT6302 / IT8512A+ / MCU 各一條", options: newOpt(LIGHT_BG) },
      { text: "在手", options: newOpt(LIGHT_BG) },
    ],
    [
      { text: "燒錄器", options: rowOpt(WHITE) },
      { text: "ST-Link V2 + STM32CubeProgrammer", options: rowOpt(WHITE) },
      { text: "SWD flash / RTT debug", options: rowOpt(WHITE) },
      { text: "在手", options: rowOpt(WHITE) },
    ],
    [
      { text: "電池 DUT", options: rowOpt(LIGHT_BG) },
      { text: "Samsung INR18650-25R 2500 mAh × 3", options: rowOpt(LIGHT_BG) },
      { text: "電池對象 (新品 + 老化樣本)", options: rowOpt(LIGHT_BG) },
      { text: "在手", options: rowOpt(LIGHT_BG) },
    ],
  ];

  s.addTable([tableHead, ...rows], {
    x: 0.5,
    y: 1.5,
    w: 12.33,
    colW: [1.8, 4.0, 5.03, 1.5],
    rowH: 0.55,
    fontSize: 12,
    fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: SOFT_LINE },
  });
}

// ============================================================
// Slide 5 - 測試階段總覽 (兩週時程軸)
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 4, "測試階段總覽", NAVY_DEEP);
  addPageFooter(s, 5, TOTAL);

  s.addText("三階段循序進行，5/06 啟動、5/19 結束；Pi 編排腳本與 Phase 1/2 平行開發。", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // === Gantt 風時程軸 ===
  const TL_X = 1.6;
  const TL_W = 11.0;
  const TL_Y = 1.9;
  const TL_H = 4.6;

  // 主橫軸
  s.addShape(pres.shapes.LINE, {
    x: TL_X,
    y: TL_Y + 0.5,
    w: TL_W,
    h: 0,
    line: { color: NAVY, width: 1.5 },
  });

  // 日期刻度 (5/06, 5/09, 5/12, 5/15, 5/19) — 共跨越 13 天
  const dateMarks = [
    { d: 0, label: "5/06\n(三)" },
    { d: 3, label: "5/09\n(六)" },
    { d: 6, label: "5/12\n(二)" },
    { d: 9, label: "5/15\n(五)" },
    { d: 13, label: "5/19\n(二)" },
  ];
  const totalDays = 13;
  dateMarks.forEach((m) => {
    const px = TL_X + (m.d / totalDays) * TL_W;
    s.addShape(pres.shapes.LINE, {
      x: px,
      y: TL_Y + 0.4,
      w: 0,
      h: 0.2,
      line: { color: NAVY, width: 1 },
    });
    s.addText(m.label, {
      x: px - 0.5,
      y: TL_Y - 0.05,
      w: 1.0,
      h: 0.5,
      fontSize: 10,
      fontFace: FONT_BODY,
      color: NAVY,
      bold: true,
      align: "center",
      valign: "bottom",
      margin: 0,
    });
  });

  // 三個 phase bar
  const phases = [
    {
      name: "Phase 1",
      title: "MCU 通訊測試",
      desc: "SWD flash · 64 MHz · I2C 通 INA226 · UART CSV log",
      start: 0,
      end: 5, // 5/06 - 5/11
      color: PHASE1_COLOR,
      y: TL_Y + 1.0,
    },
    {
      name: "Phase 2",
      title: "演算法單元測試",
      desc: "PC + GCC + CUnit · 邊界條件 + 標稱值通過 · 包 test_runner.py",
      start: 5, // 5/11
      end: 8, // 5/14
      color: PHASE2_COLOR,
      y: TL_Y + 1.95,
    },
    {
      name: "Phase 3",
      title: "系統整合 (Pi orchestrated)",
      desc: "0.2C 慢充 SOH 基準 + 5 種 CC 放電 + 9 組 List Mode + 12 hr long-run",
      start: 8, // 5/14
      end: 13, // 5/19
      color: PHASE3_COLOR,
      y: TL_Y + 2.9,
    },
  ];
  const BAR_H = 0.7;
  phases.forEach((p) => {
    const px = TL_X + (p.start / totalDays) * TL_W;
    const pw = ((p.end - p.start) / totalDays) * TL_W;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: px,
      y: p.y,
      w: pw,
      h: BAR_H,
      fill: { color: p.color },
      line: { color: p.color, width: 0 },
      rectRadius: 0.06,
    });
    s.addText(`${p.name}  ${p.title}`, {
      x: px + 0.15,
      y: p.y,
      w: pw - 0.3,
      h: BAR_H,
      fontSize: 13,
      fontFace: FONT_HEAD,
      color: WHITE,
      bold: true,
      align: "left",
      valign: "middle",
      margin: 0,
    });
    s.addText(p.desc, {
      x: px,
      y: p.y + BAR_H + 0.05,
      w: pw + 4.0,
      h: 0.4,
      fontSize: 10.5,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      align: "left",
      valign: "top",
      margin: 0,
    });
  });

  // 左側 Phase 圖例縱列 (留色塊)
  phases.forEach((p) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5,
      y: p.y,
      w: 1.0,
      h: BAR_H,
      fill: { color: WHITE },
      line: { color: p.color, width: 1.5 },
    });
    s.addText(p.name, {
      x: 0.5,
      y: p.y,
      w: 1.0,
      h: BAR_H,
      fontSize: 12,
      fontFace: FONT_HEAD,
      color: p.color,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
  });

  // 底部小註
  s.addText("Phase 2 與 Phase 3 部分平行 (5/14 unit test 收尾同時 Pi 啟動慢充)", {
    x: 0.5,
    y: 6.6,
    w: 12.33,
    h: 0.3,
    fontSize: 10,
    fontFace: FONT_BODY,
    color: MUTED,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
}

// ============================================================
// Slide 6 - Phase 1 | MCU 通訊測試
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 5, "Phase 1 ｜ MCU 通訊測試", PHASE1_COLOR);
  addPageFooter(s, 6, TOTAL);

  // 目標
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.55,
    fill: { color: WHITE },
    line: { color: PHASE1_COLOR, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: 1.0,
    w: 0.1,
    h: 0.55,
    fill: { color: PHASE1_COLOR },
    line: { color: PHASE1_COLOR, width: 0 },
  });
  s.addText(
    [
      { text: "目標 ", options: { bold: true, color: PHASE1_COLOR } },
      {
        text:
          "確認 MCU 韌體可下載、SystemClock 64 MHz 正確、INA226 I2C 通訊成功、UART CSV log 可被 Pi 讀取。",
        options: { color: DARK_TEXT },
      },
    ],
    {
      x: 0.8,
      y: 1.0,
      w: 12.0,
      h: 0.55,
      fontSize: 13,
      fontFace: FONT_BODY,
      align: "left",
      valign: "middle",
      margin: 0,
    }
  );

  // 表格
  const head = ["編號", "項目", "驗證方法", "通過條件"].map((t) => ({
    text: t,
    options: { fill: { color: PHASE1_COLOR }, color: WHITE, bold: true, align: "center", valign: "middle" },
  }));
  const cell = (txt, alt) => ({
    text: txt,
    options: { fill: { color: alt ? LIGHT_BG : WHITE }, color: DARK_TEXT, valign: "middle" },
  });
  const idCell = (txt, alt) => ({
    text: txt,
    options: {
      fill: { color: alt ? LIGHT_BG : WHITE },
      color: PHASE1_COLOR,
      bold: true,
      align: "center",
      valign: "middle",
    },
  });
  const rows = [
    [
      idCell("T1.1", false),
      cell("SWD 連線 / Erase / Flash 可重複", false),
      cell("STM32CubeProgrammer 連續 5 次 erase + flash", false),
      cell("5/5 通過、無 timeout", false),
    ],
    [
      idCell("T1.2", true),
      cell("SystemClock 64 MHz 確認", true),
      cell("MCO 輸出波形，量測 8 MHz (÷8 後)", true),
      cell("7.95 ~ 8.05 MHz", true),
    ],
    [
      idCell("T1.3", false),
      cell("INA226 Manufacturer / Die ID", false),
      cell("韌體啟動讀 0xFE / 0xFF，UART log 印出", false),
      cell("MFG=0x5449, Die=0x2260", false),
    ],
    [
      idCell("T1.4", true),
      cell("USART2 CSV header 輸出", true),
      cell("115200/8N1 接 Pi 端 pyserial 收", true),
      cell("正確收到 ts_ms,bus_v_mv,...", true),
    ],
    [
      idCell("T1.5", false),
      cell("LED 心跳 (PA5) + Pi log 連線", false),
      cell("示波器量 + Pi 端 ttyUSB log 接 5 分鐘", false),
      cell("5 Hz ± 5 % 閃爍 + 0 NACK", false),
    ],
  ];

  s.addTable([head, ...rows], {
    x: 0.5,
    y: 1.85,
    w: 12.33,
    colW: [1.0, 3.7, 4.5, 3.13],
    rowH: 0.55,
    fontSize: 12,
    fontFace: FONT_BODY,
    border: { type: "solid", pt: 0.5, color: SOFT_LINE },
  });

  // 通過條件 callout
  const CY = 5.55;
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: CY,
    w: 12.33,
    h: 1.4,
    fill: { color: WHITE },
    line: { color: PHASE1_COLOR, width: 1 },
  });
  s.addText(
    [
      {
        text: "Phase 1 通過判準",
        options: { bold: true, color: PHASE1_COLOR, fontSize: 14, breakLine: true },
      },
      {
        text:
          "T1.1 ~ T1.5 全部 PASS；任一 FAIL 必須回頭修正後重做，不得跳階段。",
        options: { color: DARK_TEXT, fontSize: 12, breakLine: true },
      },
      {
        text:
          "預估時程：5/06 ~ 5/11 (4 個工作天)；Pi SCPI/UART 探針同期搭建。",
        options: { color: MUTED, fontSize: 11, italic: true },
      },
    ],
    {
      x: 0.7,
      y: CY + 0.1,
      w: 12.0,
      h: 1.2,
      fontFace: FONT_BODY,
      align: "left",
      valign: "top",
      margin: 0,
      paraSpaceAfter: 4,
    }
  );
}

// ============================================================
// Slide 7 - Phase 2 | 演算法單元測試 (方塊圖)
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 6, "Phase 2 ｜ 演算法單元測試", PHASE2_COLOR);
  addPageFooter(s, 7, TOTAL);

  s.addText("PC 端用 GCC + CUnit 編譯 soc_soh_calc.c (link stub HAL)；資料流以方塊圖呈現。", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // === Block diagram helpers ===
  function block(x, y, w, h, fill, stroke, title, sub, titleColor) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x,
      y,
      w,
      h,
      fill: { color: fill },
      line: { color: stroke, width: 1.5 },
      rectRadius: 0.06,
    });
    const isDark = titleColor === WHITE;
    const subColor = isDark ? ICE : MUTED;
    s.addText(
      [
        { text: title, options: { bold: true, fontSize: 12, color: titleColor || DARK_TEXT, breakLine: true } },
        ...(sub
          ? [{ text: sub, options: { fontSize: 10, color: subColor, italic: true } }]
          : []),
      ],
      {
        x: x + 0.05,
        y,
        w: w - 0.1,
        h,
        fontFace: FONT_BODY,
        align: "center",
        valign: "middle",
        margin: 0,
      }
    );
  }
  function arrow(x, y, w, color, label) {
    s.addShape(pres.shapes.LINE, {
      x,
      y,
      w,
      h: 0,
      line: { color, width: 2.5, endArrowType: "triangle" },
    });
    if (label) {
      s.addText(label, {
        x,
        y: y - 0.3,
        w,
        h: 0.25,
        fontSize: 10,
        fontFace: FONT_BODY,
        color,
        bold: true,
        align: "center",
        valign: "middle",
        margin: 0,
      });
    }
  }

  // === Flow A: 動態阻抗法 SOC ===
  const FA_Y = 2.3;
  const FA_BOX_H = 1.0;
  // 標題列
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: FA_Y - 0.45,
    w: 0.18,
    h: FA_BOX_H + 0.45,
    fill: { color: PHASE2_COLOR },
    line: { color: PHASE2_COLOR, width: 0 },
  });
  s.addText("T3.1  動態阻抗法 SOC  →  soc_calc_dynamic_impedance()", {
    x: 0.75,
    y: FA_Y - 0.45,
    w: 12,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_HEAD,
    color: PHASE2_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 區塊 (Input → Algo → Output) — 單一水平流, 避免重疊
  const A_W = 2.6;
  // Input
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.75, y: FA_Y, w: A_W, h: FA_BOX_H,
    fill: { color: "EFF6FF" }, line: { color: "1E3A8A", width: 1.5 }, rectRadius: 0.06,
  });
  s.addText(
    [
      { text: "sample_before / sample_after", options: { bold: true, fontSize: 11, color: DARK_TEXT, breakLine: true } },
      { text: "V_mv,  I_mA  各一筆", options: { fontSize: 10, color: MUTED, italic: true, breakLine: true } },
      { text: "ΔV = after − before", options: { fontSize: 10, color: MUTED, italic: true, breakLine: true } },
      { text: "ΔI = after − before", options: { fontSize: 10, color: MUTED, italic: true } },
    ],
    { x: 0.85, y: FA_Y, w: A_W - 0.2, h: FA_BOX_H, fontFace: FONT_BODY, align: "center", valign: "middle", margin: 0, paraSpaceAfter: 1 }
  );
  // Algo
  block(0.75 + A_W + 0.4, FA_Y, A_W + 0.4, FA_BOX_H,
    PHASE2_COLOR, PHASE2_COLOR, "dynamic_impedance()", "Z_mohm = ΔV / ΔI", WHITE);
  // Output
  block(0.75 + 2 * (A_W + 0.4) + 0.4, FA_Y, A_W, FA_BOX_H,
    "FEF3C7", "F59E0B", "Z_mohm 輸出", "→ 預留 SOC LUT 介面");

  // 箭頭 A (兩段)
  arrow(0.75 + A_W + 0.02, FA_Y + FA_BOX_H / 2, 0.36, NAVY);
  arrow(0.75 + 2 * A_W + 0.82, FA_Y + FA_BOX_H / 2, 0.36, NAVY);

  // === Flow B: 投影法 SOH ===
  const FB_Y = 4.65;
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: FB_Y - 0.45,
    w: 0.18,
    h: FA_BOX_H + 0.45,
    fill: { color: PHASE3_COLOR },
    line: { color: PHASE3_COLOR, width: 0 },
  });
  s.addText("T3.2  投影法 SOH  →  soh_calc_projection()", {
    x: 0.75,
    y: FB_Y - 0.45,
    w: 12,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_HEAD,
    color: PHASE3_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  block(0.75, FB_Y, A_W, FA_BOX_H, "FEF2F2", "991B1B",
    "cumulative_charge", "mAh (Pi log 累積)");
  block(0.75 + A_W + 0.4, FB_Y, A_W, FA_BOX_H, "FEF2F2", "991B1B",
    "nominal_capacity", "2500 mAh");
  block(0.75 + 2 * (A_W + 0.4), FB_Y, A_W + 0.4, FA_BOX_H,
    PHASE3_COLOR, PHASE3_COLOR, "projection()", "ratio = cum / nominal", WHITE);
  block(0.75 + 3 * (A_W + 0.4) + 0.3, FB_Y, A_W, FA_BOX_H,
    "FEF3C7", "F59E0B", "SOH %", "(0 ~ 100, clamp)");

  arrow(0.75 + A_W + 0.02, FB_Y + FA_BOX_H / 2, 0.36, NAVY);
  arrow(0.75 + 2 * A_W + 0.42, FB_Y + FA_BOX_H / 2, 0.36, NAVY);
  arrow(0.75 + 3 * A_W + 1.22, FB_Y + FA_BOX_H / 2, 0.28, PHASE3_COLOR, "輸出");

  // 邊界條件小註
  const NX = 0.5;
  const NY = 6.0;
  s.addShape(pres.shapes.RECTANGLE, {
    x: NX,
    y: NY,
    w: 12.33,
    h: 0.95,
    fill: { color: WHITE },
    line: { color: SOFT_LINE, width: 1 },
  });
  s.addText("邊界條件 (必須通過)", {
    x: NX + 0.15,
    y: NY + 0.05,
    w: 4,
    h: 0.3,
    fontSize: 11,
    fontFace: FONT_HEAD,
    color: NAVY,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  s.addText(
    [
      { text: "T3.1 ", options: { bold: true, color: PHASE2_COLOR } },
      { text: "sample==NULL → false ｜ is_valid==false → false ｜ |ΔI| < 1 mA → false (避免除零)", options: { color: DARK_TEXT, breakLine: true } },
      { text: "T3.2 ", options: { bold: true, color: PHASE3_COLOR } },
      { text: "nominal ≤ 0 → false ｜ cum < 0 → ratio clamp 0 ｜ cum > nominal → ratio clamp 1.0", options: { color: DARK_TEXT } },
    ],
    {
      x: NX + 0.15,
      y: NY + 0.35,
      w: 12.0,
      h: 0.6,
      fontSize: 11,
      fontFace: FONT_BODY,
      align: "left",
      valign: "top",
      margin: 0,
      paraSpaceAfter: 2,
    }
  );
}

// ============================================================
// Slide 8 - Phase 3 | 系統整合 (Pi orchestrated 流程圖)
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 7, "Phase 3 ｜ 系統整合 (Pi orchestrated)", PHASE3_COLOR);
  addPageFooter(s, 8, TOTAL);

  s.addText("Pi 端 test_runner.py 自動驅動下列循環，全程無人值守、CSV 即時對齊儲存。", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // === 流程圖 ===
  // 上方主流程：充 → 放 → List Mode → Long-run
  const FY = 1.85;
  const STEP_W = 2.7;
  const STEP_H = 1.4;
  const GAP = 0.35;
  const FX = 0.5;

  function stepBox(x, y, w, h, color, title, body) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x,
      y,
      w,
      h,
      fill: { color: WHITE },
      line: { color, width: 2 },
      rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x,
      y,
      w,
      h: 0.4,
      fill: { color },
      line: { color, width: 0 },
    });
    s.addText(title, {
      x,
      y,
      w,
      h: 0.4,
      fontSize: 12,
      fontFace: FONT_HEAD,
      color: WHITE,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
    s.addText(body, {
      x: x + 0.1,
      y: y + 0.45,
      w: w - 0.2,
      h: h - 0.5,
      fontSize: 11,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      align: "left",
      valign: "top",
      margin: 0,
      paraSpaceAfter: 2,
    });
  }

  function flowArrow(x, y) {
    s.addShape(pres.shapes.LINE, {
      x,
      y,
      w: GAP,
      h: 0,
      line: { color: NAVY, width: 2.5, endArrowType: "triangle" },
    });
  }

  // Step 1: 慢充 SOH 基準
  stepBox(
    FX, FY, STEP_W, STEP_H,
    PHASE1_COLOR,
    "① 0.2C 慢充",
    [
      { text: "IT6302 CC-CV → 4.2V", options: { breakLine: true } },
      { text: "I = 500 mA  (~5.5 hr)", options: { breakLine: true } },
      { text: "建立 SOH ground truth", options: { italic: true, color: MUTED } },
    ]
  );
  flowArrow(FX + STEP_W, FY + STEP_H / 2);

  // Step 2: 5 種 CC 放電
  stepBox(
    FX + STEP_W + GAP, FY, STEP_W, STEP_H,
    PHASE3_COLOR,
    "② 5 種 CC 放電",
    [
      { text: "0.2C / 0.4C / 0.5C", options: { breakLine: true } },
      { text: "1C / 1.5C / 2C → 3.0V", options: { breakLine: true } },
      { text: "每輪間 0.5C 充電 ~3 hr", options: { italic: true, color: MUTED } },
    ]
  );
  flowArrow(FX + 2 * STEP_W + GAP, FY + STEP_H / 2);

  // Step 3: List Mode 動態階躍
  stepBox(
    FX + 2 * (STEP_W + GAP), FY, STEP_W, STEP_H,
    PHASE2_COLOR,
    "③ List Mode 動態",
    [
      { text: "9 組 = 3 ΔI × 3 SOC", options: { breakLine: true } },
      { text: "ΔI ∈ {0.3C, 0.5C, 1.5C}", options: { breakLine: true } },
      { text: "驗證動態阻抗演算法", options: { italic: true, color: MUTED } },
    ]
  );
  flowArrow(FX + 3 * STEP_W + 2 * GAP, FY + STEP_H / 2);

  // Step 4: 12 hr long-run
  stepBox(
    FX + 3 * (STEP_W + GAP), FY, STEP_W, STEP_H,
    NAVY,
    "④ 12 hr long-run",
    [
      { text: "5 Hz 連續取樣", options: { breakLine: true } },
      { text: "Stack 溢位回讀", options: { breakLine: true } },
      { text: "Pi 收 CSV 不掉封包", options: { italic: true, color: MUTED } },
    ]
  );

  // === 下半：Pi orchestrator 介紹 ===
  const PY = 4.0;
  // Pi 大方塊
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5,
    y: PY,
    w: 3.5,
    h: 2.7,
    fill: { color: NAVY },
    line: { color: NAVY, width: 0 },
    rectRadius: 0.1,
  });
  s.addText(
    [
      { text: "Raspberry Pi 5", options: { bold: true, color: WHITE, fontSize: 16, breakLine: true } },
      { text: "test_runner.py", options: { color: ICE, fontSize: 11, italic: true, breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 6 } },
      { text: "排程：asyncio loop", options: { color: WHITE, fontSize: 11, breakLine: true } },
      { text: "儀器：pyvisa-py + SCPI", options: { color: WHITE, fontSize: 11, breakLine: true } },
      { text: "MCU：pyserial CSV 解析", options: { color: WHITE, fontSize: 11, breakLine: true } },
      { text: "log：時間戳對齊 CSV", options: { color: WHITE, fontSize: 11, breakLine: true } },
      { text: "監看：SSH 遠端 + UPS 保護", options: { color: WHITE, fontSize: 11 } },
    ],
    {
      x: 0.7,
      y: PY + 0.15,
      w: 3.1,
      h: 2.5,
      fontFace: FONT_BODY,
      align: "left",
      valign: "top",
      margin: 0,
      paraSpaceAfter: 3,
    }
  );

  // 三條輸出箭頭 (向右)
  // 從 Pi 右邊出發 → 三個目標
  const targets = [
    {
      title: "→ IT6302 SCPI",
      body: "VOLT 4.2 / CURR 1.25 / OUTP ON ...",
      color: PHASE1_COLOR,
      y: PY + 0.1,
    },
    {
      title: "→ IT8512A+ SCPI",
      body: "MODE CC / CURR 2.5 / LIST 階梯 0~2C ...",
      color: PHASE3_COLOR,
      y: PY + 0.95,
    },
    {
      title: "→ MCU UART (Pi 收)",
      body: "USART2 CSV ts_ms,bus_v_mv,curr_ma,...",
      color: PHASE2_COLOR,
      y: PY + 1.8,
    },
  ];
  targets.forEach((t) => {
    // 箭頭
    s.addShape(pres.shapes.LINE, {
      x: 4.0,
      y: t.y + 0.4,
      w: 0.5,
      h: 0,
      line: { color: t.color, width: 2.5, endArrowType: "triangle" },
    });
    // 文字方塊
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.55,
      y: t.y,
      w: 8.28,
      h: 0.8,
      fill: { color: WHITE },
      line: { color: SOFT_LINE, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.55,
      y: t.y,
      w: 0.1,
      h: 0.8,
      fill: { color: t.color },
      line: { color: t.color, width: 0 },
    });
    s.addText(
      [
        { text: t.title, options: { bold: true, color: t.color, fontSize: 12, breakLine: true } },
        { text: t.body, options: { color: DARK_TEXT, fontSize: 11, italic: true } },
      ],
      {
        x: 4.75,
        y: t.y,
        w: 8.0,
        h: 0.8,
        fontFace: FONT_BODY,
        align: "left",
        valign: "middle",
        margin: 0,
        paraSpaceAfter: 2,
      }
    );
  });
}

// ============================================================
// Slide 9 - 預估時間表 + 風險與下一步
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: LIGHT_BG };
  addPageHeader(s, 8, "預估時間表 + 風險與下一步", NAVY_DEEP);
  addPageFooter(s, 9, TOTAL);

  s.addText("整體 2 週完成 (5/06 — 5/19)；Pi 端開發與 Phase 1/2 平行，不延後 Phase 3。", {
    x: 0.5,
    y: 1.0,
    w: 12.33,
    h: 0.4,
    fontSize: 13,
    fontFace: FONT_BODY,
    color: DARK_TEXT,
    italic: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // === 左欄：預估時間表 (mini Gantt) ===
  const LX = 0.5;
  const LY = 1.5;
  const LW = 7.8;
  const LH = 5.4;

  s.addShape(pres.shapes.RECTANGLE, {
    x: LX,
    y: LY,
    w: LW,
    h: LH,
    fill: { color: WHITE },
    line: { color: SOFT_LINE, width: 1 },
  });
  s.addText("預估時間表 (兩週甘特)", {
    x: LX + 0.15,
    y: LY + 0.1,
    w: LW - 0.3,
    h: 0.35,
    fontSize: 13,
    fontFace: FONT_HEAD,
    color: NAVY,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });

  // 時程列項
  const tasks = [
    { name: "CubeMX skeleton + Pi 環境", days: [0, 1], color: PHASE1_COLOR },
    { name: "SWD flash + SystemClock + Pi SCPI 探針", days: [1, 3], color: PHASE1_COLOR },
    { name: "INA226 ID + I2C + UART CSV log", days: [2, 3], color: PHASE1_COLOR },
    { name: "演算法 unit test (CUnit)", days: [5, 7], color: PHASE2_COLOR },
    { name: "test_runner.py 編排腳本", days: [7, 8], color: PHASE2_COLOR },
    { name: "Phase 3 D1 ─ 0.2C 慢充 + 0.2C 放電", days: [8, 9], color: PHASE3_COLOR },
    { name: "Phase 3 D2 ─ 0.5/1C 放電 + 充電循環", days: [9, 10], color: PHASE3_COLOR },
    { name: "Phase 3 D3 ─ 1.5/2C + List Mode 9 組", days: [10, 12], color: PHASE3_COLOR },
    { name: "Phase 3 D4 ─ 12 hr long-run + 收尾", days: [12, 13], color: PHASE3_COLOR },
  ];

  const ROW_H = 0.42;
  const ROW_TOP = LY + 0.65;
  const NAME_W = 3.3;
  const BAR_X0 = LX + NAME_W + 0.1;
  const BAR_W_TOTAL = LW - NAME_W - 0.3;
  const TOTAL_DAYS = 13;

  // 日期軸
  s.addShape(pres.shapes.LINE, {
    x: BAR_X0,
    y: ROW_TOP - 0.1,
    w: BAR_W_TOTAL,
    h: 0,
    line: { color: SOFT_LINE, width: 1 },
  });
  [0, 3, 6, 9, 13].forEach((d) => {
    const labelMap = { 0: "5/06", 3: "5/09", 6: "5/12", 9: "5/15", 13: "5/19" };
    const px = BAR_X0 + (d / TOTAL_DAYS) * BAR_W_TOTAL;
    s.addText(labelMap[d], {
      x: px - 0.4,
      y: ROW_TOP - 0.42,
      w: 0.8,
      h: 0.3,
      fontSize: 9,
      fontFace: FONT_BODY,
      color: NAVY,
      bold: true,
      align: "center",
      valign: "middle",
      margin: 0,
    });
    s.addShape(pres.shapes.LINE, {
      x: px,
      y: ROW_TOP - 0.1,
      w: 0,
      h: tasks.length * ROW_H + 0.1,
      line: { color: SOFT_LINE, width: 0.5, dashType: "dash" },
    });
  });

  tasks.forEach((t, i) => {
    const y = ROW_TOP + i * ROW_H + 0.05;
    s.addText(t.name, {
      x: LX + 0.15,
      y,
      w: NAME_W,
      h: ROW_H - 0.1,
      fontSize: 10,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      align: "left",
      valign: "middle",
      margin: 0,
    });
    const bx = BAR_X0 + (t.days[0] / TOTAL_DAYS) * BAR_W_TOTAL;
    const bw = ((t.days[1] - t.days[0]) / TOTAL_DAYS) * BAR_W_TOTAL;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: bx,
      y: y + 0.05,
      w: Math.max(bw, 0.15),
      h: ROW_H - 0.2,
      fill: { color: t.color },
      line: { color: t.color, width: 0 },
      rectRadius: 0.04,
    });
  });

  // === 右欄：風險與下一步 ===
  const RX2 = 8.5;
  const RY = 1.5;
  const RW = 4.33;

  // 風險
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX2,
    y: RY,
    w: RW,
    h: 2.85,
    fill: { color: WHITE },
    line: { color: PHASE3_COLOR, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX2,
    y: RY,
    w: 0.1,
    h: 2.85,
    fill: { color: PHASE3_COLOR },
    line: { color: PHASE3_COLOR, width: 0 },
  });
  s.addText("風險", {
    x: RX2 + 0.25,
    y: RY + 0.1,
    w: RW - 0.4,
    h: 0.35,
    fontSize: 14,
    fontFace: FONT_HEAD,
    color: PHASE3_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  s.addText(
    [
      { text: "INA226 模組來源未驗證，需排除偽冒品", options: { bullet: { code: "25B8" }, breakLine: true } },
      { text: "Kelvin shunt 走線過長 → 寄生感性誤差", options: { bullet: { code: "25B8" }, breakLine: true } },
      { text: "2C 放電 5A 接點 / 線材熱風險", options: { bullet: { code: "25B8" }, breakLine: true } },
      { text: "12 hr long-run 期間 Pi 斷電 → 建議插 UPS", options: { bullet: { code: "25B8" }, breakLine: true } },
      { text: "SOC ↔ Z LUT 未建表，Phase 2 僅算 Z 不轉 SOC", options: { bullet: { code: "25B8" } } },
    ],
    {
      x: RX2 + 0.25,
      y: RY + 0.5,
      w: RW - 0.4,
      h: 2.3,
      fontSize: 11,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      paraSpaceAfter: 4,
      valign: "top",
      margin: 0,
    }
  );

  // 下一步
  const NSY = RY + 3.0;
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX2,
    y: NSY,
    w: RW,
    h: 2.4,
    fill: { color: WHITE },
    line: { color: PHASE1_COLOR, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX2,
    y: NSY,
    w: 0.1,
    h: 2.4,
    fill: { color: PHASE1_COLOR },
    line: { color: PHASE1_COLOR, width: 0 },
  });
  s.addText("下一步 (本週)", {
    x: RX2 + 0.25,
    y: NSY + 0.1,
    w: RW - 0.4,
    h: 0.35,
    fontSize: 14,
    fontFace: FONT_HEAD,
    color: PHASE1_COLOR,
    bold: true,
    align: "left",
    valign: "middle",
    margin: 0,
  });
  s.addText(
    [
      { text: "5/07  CubeMX 產 HAL skeleton + Pi OS / Python 環境", options: { bullet: { code: "2713" }, breakLine: true } },
      { text: "5/08  Pi 端 SCPI 探針通 IT6302 / IT8512A+", options: { bullet: { code: "2713" }, breakLine: true } },
      { text: "5/11  T1.1 ~ T1.5 完成，Phase 1 收斂", options: { bullet: { code: "2713" }, breakLine: true } },
      { text: "5/13  test_runner.py 編排腳本完工", options: { bullet: { code: "2713" } } },
    ],
    {
      x: RX2 + 0.25,
      y: NSY + 0.5,
      w: RW - 0.4,
      h: 1.85,
      fontSize: 11,
      fontFace: FONT_BODY,
      color: DARK_TEXT,
      paraSpaceAfter: 4,
      valign: "top",
      margin: 0,
    }
  );
}

// ============================================================
// Output
// ============================================================
const outPath = path.resolve(__dirname, "..", "..", "DOC", "會議紀錄", "meeting_0506_洪大甲.pptx");
pres
  .writeFile({ fileName: outPath })
  .then((file) => {
    console.log("✓ Wrote:", file);
  })
  .catch((err) => {
    console.error("✗ Error:", err);
    process.exit(1);
  });
