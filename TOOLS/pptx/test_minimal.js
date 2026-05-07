const path = require("path");
require("module").Module._initPaths();
const PptxGenJS = require(path.join(process.env.APPDATA, "npm", "node_modules", "pptxgenjs"));

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE";

const s = pres.addSlide();
s.background = { color: "F8FAFC" };
s.addText("Hello 測試", {
  x: 1, y: 1, w: 8, h: 1,
  fontSize: 24, fontFace: "Microsoft JhengHei", color: "1E2761", bold: true,
});

const out = path.resolve(__dirname, "qa", "minimal.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("Wrote:", f));
